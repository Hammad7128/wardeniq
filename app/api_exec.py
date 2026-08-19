
import json
import os
import re

import httpx

# Only these ever get sent. A test case that asks for something else is skipped rather
# than executed, so a malformed/hallucinated method can't turn into a surprise request.
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}

# Methods that change state. Blocked unless the operator explicitly opts in, because the
# usual target is a shared staging environment.
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

DEFAULT_TIMEOUT = float(os.getenv("API_EXEC_TIMEOUT_SECONDS", "20"))

_PLACEHOLDER_RE = re.compile(r"[{:<][\w-]+[}>]?")


class ExecConfig:
    """Where and how to fire requests. No base_url == execution disabled."""

    def __init__(self, base_url: str = "", headers: dict | None = None,
                 timeout: float = DEFAULT_TIMEOUT, allow_mutating: bool = False,
                 verify_tls: bool = True, path_params: dict | None = None):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.headers = dict(headers or {})
        self.timeout = float(timeout or DEFAULT_TIMEOUT)
        self.allow_mutating = bool(allow_mutating)
        self.verify_tls = bool(verify_tls)
        # Substitutions for templated segments, e.g. {"id": "42"} for /users/{id}.
        self.path_params = dict(path_params or {})

    def enabled(self) -> bool:
        return bool(self.base_url)

    @classmethod
    def from_env(cls):
        raw_headers = os.getenv("API_EXEC_HEADERS", "")
        headers = {}
        if raw_headers:
            try:
                headers = {str(k): str(v) for k, v in json.loads(raw_headers).items()}
            except (json.JSONDecodeError, AttributeError, TypeError):
                headers = {}
        return cls(
            base_url=os.getenv("API_EXEC_BASE_URL", ""),
            headers=headers,
            timeout=float(os.getenv("API_EXEC_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT))),
            allow_mutating=os.getenv("API_EXEC_ALLOW_MUTATING", "false").lower() == "true",
            verify_tls=os.getenv("API_EXEC_VERIFY_TLS", "true").lower() != "false",
        )


def request_spec(case: dict) -> dict:
    """Pull the executable request out of a test case, or explain why there isn't one.

    Reads the structured fields API generation already produces (`method`, `endpoint`,
    `expected_result.status_code`) plus the optional `request` block that
    `prompt_builder` now asks for. Returns {"ok": False, "reason": ...} when the case
    isn't mechanically executable — a case is never guessed into a request.
    """
    _meta = case.get("metadata")
    meta: dict = _meta if isinstance(_meta, dict) else {}
    src = {**meta, **{k: v for k, v in case.items() if k != "metadata"}}

    method = str(src.get("method") or "").strip().upper()
    endpoint = str(src.get("endpoint") or src.get("path") or "").strip()
    if not method or not endpoint:
        return {"ok": False, "reason": "case has no method/endpoint to execute"}
    if method not in SAFE_METHODS:
        return {"ok": False, "reason": f"unsupported method {method!r}"}
    if not endpoint.startswith("/"):
        return {"ok": False, "reason": f"endpoint {endpoint!r} is not a path"}

    expected = src.get("expected_result")
    status = None
    if isinstance(expected, dict):
        status = expected.get("status_code")
    if status is None:
        status = src.get("status_code")
    try:
        status = int(str(status).strip()) if status is not None else None
    except (TypeError, ValueError):
        status = None
    if status is None:
        return {"ok": False, "reason": "case has no expected status code to assert"}

    _req = src.get("request")
    req: dict = _req if isinstance(_req, dict) else {}
    spec = {
        "ok": True,
        "method": method,
        "endpoint": endpoint,
        "expected_status": status,
        "body": req.get("body") if isinstance(req.get("body"), (dict, list)) else None,
        "query": req.get("query") if isinstance(req.get("query"), dict) else None,
        "headers": req.get("headers") if isinstance(req.get("headers"), dict) else None,
    }
    asserts = src.get("response_assertions")
    if isinstance(asserts, dict):
        spec["body_contains"] = [str(s) for s in (asserts.get("contains") or [])][:10]
        spec["body_excludes"] = [str(s) for s in (asserts.get("excludes") or [])][:10]
        spec["json_keys"] = [str(s) for s in (asserts.get("json_keys") or [])][:10]
    return spec


def resolve_path(endpoint: str, path_params: dict) -> tuple:
    """Substitute templated segments. Returns (path, unresolved_placeholders)."""
    path = endpoint
    for key, val in (path_params or {}).items():
        for pat in ("{%s}" % key, ":%s" % key, "<%s>" % key):
            path = path.replace(pat, str(val))
    return path, _PLACEHOLDER_RE.findall(path)


def _assert_response(spec: dict, status_code: int, text: str) -> tuple:
    """Compare an observed response to the case's expectation. Returns (passed, checks)."""
    checks = [{"check": "status_code", "expected": spec["expected_status"],
               "actual": status_code, "passed": status_code == spec["expected_status"]}]
    for needle in spec.get("body_contains") or []:
        checks.append({"check": "body_contains", "expected": needle,
                       "passed": needle in text})
    for needle in spec.get("body_excludes") or []:
        checks.append({"check": "body_excludes", "expected": needle,
                       "passed": needle not in text})
    keys = spec.get("json_keys") or []
    if keys:
        try:
            payload = json.loads(text or "")
        except (json.JSONDecodeError, TypeError):
            payload = None
        for key in keys:
            present = isinstance(payload, dict) and key in payload
            checks.append({"check": "json_key", "expected": key, "passed": bool(present)})
    return all(c["passed"] for c in checks), checks


def execute_case(case: dict, config: ExecConfig, client=None) -> dict:
    """Fire one API case and report what actually happened.

    Result `status` is one of:
      * 'passed'  — request sent, every assertion held
      * 'failed'  — request sent, an assertion did not hold (a real, cited failure)
      * 'skipped' — not executable (missing data, mutating while disallowed, no target)
      * 'error'   — the request itself could not complete (connection/timeout)

    `verification` records that this is a status/body-level check only, so no caller can
    mistake a pass for full behavioural proof.
    """
    out = {"test_case_id": case.get("id") or case.get("test_case_id"),
           "title": case.get("title"), "verification": "http_status_and_body"}

    if not config.enabled():
        return {**out, "status": "skipped",
                "reason": "no API_EXEC_BASE_URL configured (execution disabled)"}

    spec = request_spec(case)
    if not spec.get("ok"):
        return {**out, "status": "skipped", "reason": spec.get("reason")}
    if spec["method"] in MUTATING_METHODS and not config.allow_mutating:
        return {**out, "status": "skipped",
                "reason": f"{spec['method']} blocked (set API_EXEC_ALLOW_MUTATING=true "
                          "to permit state-changing requests against this target)"}

    path, unresolved = resolve_path(spec["endpoint"], config.path_params)
    if unresolved:
        # Firing /users/{id} literally would test nothing real, so refuse rather than
        # produce a meaningless 404 and call it a failure.
        return {**out, "status": "skipped",
                "reason": f"unresolved path parameter(s): {', '.join(unresolved)}"}

    url = f"{config.base_url}{path}"
    headers = {**config.headers, **(spec.get("headers") or {})}
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=config.timeout, verify=config.verify_tls,
                              follow_redirects=True)
    try:
        resp = client.request(spec["method"], url, headers=headers or None,
                              params=spec.get("query") or None,
                              json=spec.get("body") if spec.get("body") is not None else None)
        text = resp.text or ""
        passed, checks = _assert_response(spec, resp.status_code, text)
        return {**out, "status": "passed" if passed else "failed",
                "request": {"method": spec["method"], "url": url},
                "response_status": resp.status_code,
                "checks": checks,
                "response_excerpt": text[:500]}
    except httpx.HTTPError as e:
        return {**out, "status": "error",
                "request": {"method": spec["method"], "url": url},
                "reason": f"{type(e).__name__}: {e}"}
    finally:
        if own_client:
            client.close()


def execute_cases(cases, config: ExecConfig, client=None) -> dict:
    """Execute a batch of API cases. Returns per-case results plus a summary.

    `executed` counts only cases that actually sent a request, so a run where everything
    was skipped can never be mistaken for a clean pass.
    """
    results = []
    own_client = client is None
    if own_client and config.enabled():
        client = httpx.Client(timeout=config.timeout, verify=config.verify_tls,
                              follow_redirects=True)
    try:
        for case in cases or []:
            results.append(execute_case(case, config, client=client))
    finally:
        if own_client and client is not None:
            client.close()
    counts = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    executed = counts["passed"] + counts["failed"]
    return {
        "results": results,
        "summary": {
            **counts,
            "total": len(results),
            "executed": executed,
            # Deliberately None (not 100%) when nothing ran, so an all-skipped run
            # cannot render as a perfect score.
            "pass_rate": round(counts["passed"] / executed, 3) if executed else None,
            "verification": "http_status_and_body",
            "note": ("Status/body assertions only — database side effects and "
                     "negative assertions are not verified by execution."),
        },
    }
