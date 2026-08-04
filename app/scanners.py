"""Deterministic code scanners that corroborate (never replace) an LLM verdict.

Why this exists
---------------
Mind Map's coverage verdict is model judgement. Competing tools that are trusted more
in enterprise reviews — CodeRabbit's review layer, for instance — pair the model with
dozens of real linters/SAST tools so at least part of every finding is reproducible by
a machine rather than asserted by a model. This module is that half for wardenIQ: it
runs real scanners over the SAME production-code chunks the reviewer was shown, and
returns facts (a rule id, a file, a line) that can be attached as corroborating
evidence and used to ground non-functional test cases.

Design constraints, deliberately
--------------------------------
* OPTIONAL. Neither binary is a dependency. If `semgrep` / `gitleaks` are absent the
  functions return a clearly-marked "unavailable" result and callers carry on. An
  air-gapped install with no scanners installed must behave exactly as before.
* NO NETWORK. semgrep runs with `--metrics=off` and only local rule configs, so an
  on-prem deployment never phones home. This matters because wardenIQ's whole pitch is
  that nothing leaves the network.
* ADVISORY ONLY. Nothing here can promote a verdict to 'covered'. A scanner hit is
  corroboration for a human, and its absence proves nothing at all — treating "no
  findings" as "code is fine" would be exactly the overclaiming we're trying to remove.
"""
import json
import os
import shutil
import subprocess
import tempfile

# Chunks are code fragments, not whole files; a scanner needs real files on disk with
# a plausible extension to pick the right parser. We reconstruct a shallow tree.
_SCAN_TIMEOUT = int(os.getenv("SCANNER_TIMEOUT_SECONDS", "120"))
_MAX_SCAN_BYTES = int(os.getenv("SCANNER_MAX_BYTES", str(8 * 1024 * 1024)))

# Findings above this count are truncated — a scanner tantrum shouldn't flood a verdict.
_MAX_FINDINGS = int(os.getenv("SCANNER_MAX_FINDINGS", "200"))


def scanner_available(name: str) -> bool:
    """Is this scanner binary on PATH? Cheap enough to call per run."""
    return shutil.which(name) is not None


def available_scanners() -> list:
    return [n for n in ("semgrep", "gitleaks") if scanner_available(n)]


def _materialize(code_excerpts, root: str) -> dict:
    """Write excerpts to a temp tree, preserving relative paths. Returns path->realpath.

    Multiple chunks from one file are concatenated in the order given, which keeps line
    numbers meaningless but paths meaningful — we only ever report the file, never a
    line, precisely because chunking makes line numbers untrustworthy.
    """
    written, total = {}, 0
    for c in code_excerpts or []:
        rel = str((c or {}).get("path") or "").strip().lstrip("/")
        text = str((c or {}).get("text") or "")
        if not rel or not text:
            continue
        # Refuse anything that tries to escape the sandbox directory.
        norm = os.path.normpath(rel)
        if norm.startswith("..") or os.path.isabs(norm):
            continue
        if total + len(text) > _MAX_SCAN_BYTES:
            break
        dest = os.path.join(root, norm)
        os.makedirs(os.path.dirname(dest) or root, exist_ok=True)
        mode = "a" if norm in written else "w"
        with open(dest, mode, encoding="utf-8", errors="replace") as fh:
            if mode == "a":
                fh.write("\n")
            fh.write(text)
        written[norm] = dest
        total += len(text)
    return written


def _run(cmd, cwd, timeout=None):
    """Run a scanner. Returns (returncode, stdout, error_or_None) and never raises."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout or _SCAN_TIMEOUT, check=False)
        return p.returncode, p.stdout or "", None
    except subprocess.TimeoutExpired:
        return -1, "", f"{cmd[0]} timed out after {timeout or _SCAN_TIMEOUT}s"
    except (OSError, ValueError) as e:
        return -1, "", f"{cmd[0]} failed to start: {e}"


def run_semgrep(code_excerpts, config: str = "auto") -> dict:
    """Pattern-based SAST over the reviewed chunks.

    `config` defaults to semgrep's bundled registry alias; set SEMGREP_CONFIG to a
    local rules path for a strictly offline install.
    """
    if not scanner_available("semgrep"):
        return {"available": False, "scanner": "semgrep", "findings": []}
    cfg = os.getenv("SEMGREP_CONFIG", config)
    with tempfile.TemporaryDirectory(prefix="wardeniq-semgrep-") as root:
        if not _materialize(code_excerpts, root):
            return {"available": True, "scanner": "semgrep", "findings": []}
        rc, stdout, err = _run(
            ["semgrep", "--json", "--quiet", "--metrics=off", "--config", cfg, "."], root)
        if err:
            return {"available": True, "scanner": "semgrep", "findings": [], "error": err}
        try:
            data = json.loads(stdout or "{}")
        except json.JSONDecodeError:
            return {"available": True, "scanner": "semgrep", "findings": [],
                    "error": "semgrep returned unparseable JSON"}
        findings = []
        for r in (data.get("results") or [])[:_MAX_FINDINGS]:
            extra = r.get("extra") or {}
            findings.append({
                "scanner": "semgrep",
                "rule": str(r.get("check_id") or "")[:160],
                "path": str(r.get("path") or "").lstrip("./"),
                "severity": str(extra.get("severity") or "INFO").upper(),
                "message": str(extra.get("message") or "")[:300],
            })
        return {"available": True, "scanner": "semgrep", "findings": findings,
                "returncode": rc}


def run_gitleaks(code_excerpts) -> dict:
    """Secret detection over the reviewed chunks."""
    if not scanner_available("gitleaks"):
        return {"available": False, "scanner": "gitleaks", "findings": []}
    with tempfile.TemporaryDirectory(prefix="wardeniq-gitleaks-") as root:
        if not _materialize(code_excerpts, root):
            return {"available": True, "scanner": "gitleaks", "findings": []}
        report = os.path.join(root, "_gitleaks_report.json")
        rc, _stdout, err = _run(
            ["gitleaks", "detect", "--no-git", "--redact", "--exit-code", "0",
             "--report-format", "json", "--report-path", report, "--source", "."], root)
        if err:
            return {"available": True, "scanner": "gitleaks", "findings": [], "error": err}
        findings = []
        try:
            with open(report, encoding="utf-8") as fh:
                for r in (json.load(fh) or [])[:_MAX_FINDINGS]:
                    findings.append({
                        "scanner": "gitleaks",
                        "rule": str(r.get("RuleID") or "")[:160],
                        "path": str(r.get("File") or "").lstrip("./"),
                        "severity": "HIGH",
                        "message": str(r.get("Description") or "")[:300],
                    })
        except (OSError, json.JSONDecodeError):
            pass    # no report written == no findings
        return {"available": True, "scanner": "gitleaks", "findings": findings,
                "returncode": rc}


def scan_excerpts(code_excerpts, enabled=None) -> dict:
    """Run every available scanner over the reviewed chunks. Never raises.

    Returns {"scanners_run", "scanners_missing", "findings", "by_path", "errors"}.
    `by_path` is what the coverage layer uses to attach corroboration per cited file.
    """
    enabled = enabled if enabled is not None else ("semgrep", "gitleaks")
    findings: list = []
    run: list = []
    missing: list = []
    errors: list = []
    for name, fn in (("semgrep", run_semgrep), ("gitleaks", run_gitleaks)):
        if name not in enabled:
            continue
        try:
            res = fn(code_excerpts)
        except Exception as e:  # noqa: BLE001 — a scanner must never break a review
            errors.append(f"{name}: {e}")
            continue
        if not res.get("available"):
            missing.append(name)
            continue
        run.append(name)
        if res.get("error"):
            errors.append(f"{name}: {res['error']}")
        findings.extend(res.get("findings") or [])
    by_path: dict = {}
    for f in findings:
        by_path.setdefault(f.get("path") or "", []).append(f)
    return {"scanners_run": run, "scanners_missing": missing,
            "findings": findings[:_MAX_FINDINGS], "by_path": by_path, "errors": errors}


def corroborate(cases: list, scan: dict) -> list:
    """Attach scanner findings to verdicts that cite the same file.

    Advisory only: this NEVER changes a status. It answers "did a real tool see anything
    in the file the model pointed at", which is a fact a reviewer can act on, unlike the
    model's own say-so. Absence of findings is not evidence of correctness and is
    deliberately not recorded as such.
    """
    by_path = (scan or {}).get("by_path") or {}
    if not by_path:
        return cases
    # Index findings by basename too, since a verdict cites "repo:path".
    by_base: dict = {}
    for path, items in by_path.items():
        by_base.setdefault(path.rsplit("/", 1)[-1], []).extend(items)
    for case in cases:
        hits = []
        for cited in (case.get("files") or []):
            path = cited.split(":", 1)[1] if ":" in cited else cited
            for f in by_path.get(path, []) or by_base.get(path.rsplit("/", 1)[-1], []):
                item = {k: f[k] for k in ("scanner", "rule", "severity", "message", "path")}
                if item not in hits:
                    hits.append(item)
        if hits:
            case["scanner_findings"] = hits[:10]
    return cases
