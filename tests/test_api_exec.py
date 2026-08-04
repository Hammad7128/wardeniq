"""Tests for real API-case execution — the one wardenIQ signal grounded in observed fact.

All requests are served by an httpx MockTransport, so these run offline and assert on
wardenIQ's own request-building and assertion logic rather than on a live service.
"""
import httpx
import pytest
from api_exec import (
    ExecConfig,
    execute_case,
    execute_cases,
    request_spec,
    resolve_path,
)


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _case(**over):
    base = {"id": "c1", "title": "Login returns a token", "method": "POST",
            "endpoint": "/api/login", "expected_result": {"status_code": 200}}
    base.update(over)
    return base


class TestRequestSpec:
    def test_extracts_method_endpoint_and_status(self):
        s = request_spec(_case())
        assert s["ok"] is True
        assert (s["method"], s["endpoint"], s["expected_status"]) == ("POST", "/api/login", 200)

    def test_reads_fields_out_of_metadata(self):
        # Persisted cases keep the structured API fields under `metadata`.
        case = {"id": "c1", "title": "t",
                "metadata": {"method": "get", "endpoint": "/api/health",
                             "expected_result": {"status_code": 200}}}
        s = request_spec(case)
        assert s["ok"] is True and s["method"] == "GET"

    def test_missing_status_is_not_executable(self):
        s = request_spec(_case(expected_result={}))
        assert s["ok"] is False and "expected status" in s["reason"]

    def test_missing_endpoint_is_not_executable(self):
        s = request_spec(_case(endpoint=""))
        assert s["ok"] is False

    def test_non_path_endpoint_is_rejected(self):
        s = request_spec(_case(endpoint="api/login"))
        assert s["ok"] is False and "not a path" in s["reason"]

    def test_unsupported_method_is_rejected(self):
        s = request_spec(_case(method="TRACE"))
        assert s["ok"] is False and "unsupported method" in s["reason"]

    def test_picks_up_body_and_assertions(self):
        s = request_spec(_case(request={"body": {"email": "a@b.c"}, "query": {"x": "1"}},
                               response_assertions={"contains": ["token"],
                                                    "json_keys": ["token"]}))
        assert s["body"] == {"email": "a@b.c"}
        assert s["query"] == {"x": "1"}
        assert s["body_contains"] == ["token"] and s["json_keys"] == ["token"]


class TestResolvePath:
    def test_substitutes_templated_segments(self):
        path, unresolved = resolve_path("/api/users/{id}", {"id": 42})
        assert path == "/api/users/42" and unresolved == []

    def test_reports_unresolved_placeholders(self):
        path, unresolved = resolve_path("/api/users/{id}/posts/{postId}", {"id": 1})
        assert "{postId}" in unresolved


class TestExecuteCase:
    def test_disabled_without_base_url(self):
        r = execute_case(_case(), ExecConfig())
        assert r["status"] == "skipped" and "API_EXEC_BASE_URL" in r["reason"]

    def test_mutating_blocked_by_default(self):
        cfg = ExecConfig(base_url="http://t")
        r = execute_case(_case(method="POST"), cfg)
        assert r["status"] == "skipped" and "API_EXEC_ALLOW_MUTATING" in r["reason"]

    def test_passing_case_reports_observed_status(self):
        cfg = ExecConfig(base_url="http://t")
        with _client(lambda req: httpx.Response(200, json={"token": "x"})) as c:
            r = execute_case(_case(method="GET", endpoint="/api/me"), cfg, client=c)
        assert r["status"] == "passed"
        assert r["response_status"] == 200
        assert r["verification"] == "http_status_and_body"

    def test_status_mismatch_is_a_real_failure(self):
        cfg = ExecConfig(base_url="http://t")
        with _client(lambda req: httpx.Response(500, text="boom")) as c:
            r = execute_case(_case(method="GET", endpoint="/api/me"), cfg, client=c)
        assert r["status"] == "failed"
        status_check = next(x for x in r["checks"] if x["check"] == "status_code")
        assert status_check == {"check": "status_code", "expected": 200,
                               "actual": 500, "passed": False}

    def test_body_contains_and_excludes_are_asserted(self):
        cfg = ExecConfig(base_url="http://t")
        case = _case(method="GET", endpoint="/api/me",
                     response_assertions={"contains": ["token"], "excludes": ["error"]})
        with _client(lambda req: httpx.Response(200, text='{"token":"abc"}')) as c:
            assert execute_case(case, cfg, client=c)["status"] == "passed"
        with _client(lambda req: httpx.Response(200, text='{"error":"nope"}')) as c:
            r = execute_case(case, cfg, client=c)
        assert r["status"] == "failed"
        assert any(x["check"] == "body_contains" and not x["passed"] for x in r["checks"])

    def test_json_key_assertion(self):
        cfg = ExecConfig(base_url="http://t")
        case = _case(method="GET", endpoint="/api/me",
                     response_assertions={"json_keys": ["token"]})
        with _client(lambda req: httpx.Response(200, json={"other": 1})) as c:
            r = execute_case(case, cfg, client=c)
        assert r["status"] == "failed"

    def test_unresolved_placeholder_is_skipped_not_failed(self):
        # Firing /users/{id} literally would produce a meaningless 404 that looks like a
        # genuine product defect. Skipping is the honest outcome.
        cfg = ExecConfig(base_url="http://t")
        with _client(lambda req: httpx.Response(404)) as c:
            r = execute_case(_case(method="GET", endpoint="/api/users/{id}"), cfg, client=c)
        assert r["status"] == "skipped" and "unresolved path parameter" in r["reason"]

    def test_connection_error_is_error_not_failure(self):
        # A dead target must never be reported as a failing test.
        def boom(req):
            raise httpx.ConnectError("refused", request=req)
        cfg = ExecConfig(base_url="http://t")
        with _client(boom) as c:
            r = execute_case(_case(method="GET", endpoint="/api/me"), cfg, client=c)
        assert r["status"] == "error" and "ConnectError" in r["reason"]

    def test_mutating_allowed_when_opted_in_and_sends_body(self):
        seen = {}

        def handler(req):
            seen["method"] = req.method
            seen["body"] = req.content
            return httpx.Response(201, json={"id": 1})

        cfg = ExecConfig(base_url="http://t", allow_mutating=True)
        case = _case(method="POST", endpoint="/api/events",
                     expected_result={"status_code": 201},
                     request={"body": {"title": "offsite"}})
        with _client(handler) as c:
            r = execute_case(case, cfg, client=c)
        assert r["status"] == "passed"
        assert seen["method"] == "POST"
        assert b"offsite" in seen["body"]

    def test_configured_headers_are_sent(self):
        seen = {}

        def handler(req):
            seen["auth"] = req.headers.get("authorization")
            return httpx.Response(200)

        cfg = ExecConfig(base_url="http://t", headers={"Authorization": "Bearer t"})
        with _client(handler) as c:
            execute_case(_case(method="GET", endpoint="/api/me"), cfg, client=c)
        assert seen["auth"] == "Bearer t"


class TestExecuteCases:
    def test_summary_counts_and_pass_rate(self):
        cfg = ExecConfig(base_url="http://t")
        cases = [_case(id="a", method="GET", endpoint="/ok"),
                 _case(id="b", method="GET", endpoint="/bad"),
                 _case(id="c", method="GET", endpoint="/x", expected_result={})]

        def handler(req):
            return httpx.Response(200 if req.url.path == "/ok" else 500)

        with _client(handler) as c:
            out = execute_cases(cases, cfg, client=c)
        s = out["summary"]
        assert (s["passed"], s["failed"], s["skipped"]) == (1, 1, 1)
        assert s["executed"] == 2
        assert s["pass_rate"] == 0.5

    def test_all_skipped_run_has_no_pass_rate(self):
        # Guards the worst possible bug here: an all-skipped run rendering as 100%.
        out = execute_cases([_case()], ExecConfig())
        assert out["summary"]["executed"] == 0
        assert out["summary"]["pass_rate"] is None

    def test_empty_input(self):
        out = execute_cases([], ExecConfig(base_url="http://t"))
        assert out["summary"]["total"] == 0 and out["summary"]["pass_rate"] is None


class TestExecConfigFromEnv:
    def test_disabled_when_no_base_url(self, monkeypatch):
        monkeypatch.delenv("API_EXEC_BASE_URL", raising=False)
        assert ExecConfig.from_env().enabled() is False

    def test_reads_headers_json(self, monkeypatch):
        monkeypatch.setenv("API_EXEC_BASE_URL", "http://staging")
        monkeypatch.setenv("API_EXEC_HEADERS", '{"Authorization":"Bearer z"}')
        cfg = ExecConfig.from_env()
        assert cfg.enabled() and cfg.headers["Authorization"] == "Bearer z"

    def test_malformed_headers_json_does_not_crash(self, monkeypatch):
        monkeypatch.setenv("API_EXEC_BASE_URL", "http://staging")
        monkeypatch.setenv("API_EXEC_HEADERS", "not json")
        assert ExecConfig.from_env().headers == {}

    @pytest.mark.parametrize("value,expected", [("true", True), ("false", False)])
    def test_allow_mutating_flag(self, monkeypatch, value, expected):
        monkeypatch.setenv("API_EXEC_BASE_URL", "http://staging")
        monkeypatch.setenv("API_EXEC_ALLOW_MUTATING", value)
        assert ExecConfig.from_env().allow_mutating is expected
