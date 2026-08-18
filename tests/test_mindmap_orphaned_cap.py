"""Tests for the `contract_findings` wiring added to `coverage.py::review_code_coverage` —
the Mind Map half of the Phase 1 cross-file dependency fix. The PR-Coverage/Code-Analysis half
is covered by tests/test_coverage_contract_cap.py; the underlying snapshot-only detector is
covered by tests/test_contracts_orphaned_reads.py.

Real AUTH-007 fixture data throughout (same files as the other contract tests). A `FakeLLM`
stands in for the real model, since none is available in this sandbox — these tests exercise
the deterministic evidence-injection and cap logic, which is exactly the part that must hold
regardless of what any LLM says (the benchmark evidence shows the real LLM had this evidence
and still got it wrong, which is precisely why the cap does not trust it on this question).
"""
import os

from conftest import FakeLLM

import contracts
import coverage as cov

import pytest

pytestmark = pytest.mark.skip(
    reason=
    "fixtures in tests/fixtures/auth_pilot/ were pulled from an external benchmark repo as a local-only experiment and were never committed (by design, per the original author's local-only constraint); the originals are not recoverable. The feature under test (contracts.py's build_contract_breaks/find_orphaned_contract_reads, wired into coverage.py/grounding.py/codeanalysis_worker.py) remains live in production, untested until real fixtures are reconstructed."
)

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


def _excerpts():
    """Mind Map's code_excerpts shape: [{"repo","path","text"}]. Uses repo="" so citations in
    the prompt are plain paths, matching how the real prompt header renders for these tests."""
    files = {
        "services/auth_service/middleware.py": "middleware.py.txt",
        "services/auth_service/refresh.py": "refresh.py.txt",
        "services/auth_service/driver_only.py": "driver_only.py.txt",
        "services/auth_service/tokens.py": "tokens_after.py.txt",
    }
    return [{"repo": "", "path": p, "text": _read(fname)} for p, fname in files.items()]


def _repo_files():
    return [{"path": p, "text": e["text"]} for p, e in
            zip(("services/auth_service/middleware.py", "services/auth_service/refresh.py",
                 "services/auth_service/driver_only.py", "services/auth_service/tokens.py"),
                _excerpts())]


def _findings():
    return contracts.find_orphaned_contract_reads(_repo_files())


def _cases():
    return [
        # Real generated step text (from an actual manual PR #9 run), not empty/title-only —
        # a title-only version of this case (no mention of "role") used to pass only via an
        # incidental collision on a consumer's fallback-default literal, since fixed (see
        # grounding._mask_fallback_default). The real steps mention "role" directly.
        {"id": "tab-aut-19", "title": "Driver-Only Endpoint Rejects Non-Driver Tokens",
         "type": "functional", "steps": [
             {"action": "A user with 'rider' role logs in and obtains an access token.",
              "expected": "System issues a valid access token with 'rider' role."},
             {"action": "The user attempts to access a protected endpoint marked as "
                        "'driver-only' using their 'rider' access token.",
              "expected": "The protected endpoint's middleware processes the request."},
         ]},
        {"id": "tab-aut-30", "title": "Role-Based Access Control for Driver-Only Endpoint",
         "type": "functional", "steps": []},
        {"id": "tab-aut-25", "title": "Successful Login Attempts Are Recorded in Audit Log",
         "type": "functional", "steps": []},
    ]


class TestFindingsPrecondition:
    def test_the_real_snapshot_actually_produces_the_expected_finding(self):
        """Sanity check on the test fixtures themselves before trusting the tests built on
        top of them — see test_contracts_orphaned_reads.py for the full dedicated coverage."""
        findings = _findings()
        assert len(findings) == 1
        assert findings[0]["old_key"] == "role"


class TestBackwardCompatibility:
    def test_omitting_contract_findings_is_unchanged(self):
        llm = FakeLLM(response={"cases": [
            {"test_case_id": "tab-aut-19", "status": "covered", "confidence": 0.9,
             "rationale": "require_role enforces roles", "files": ["services/auth_service/middleware.py"]}]})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts())
        assert "contract_findings_considered" not in out
        by_id = {c["test_case_id"]: c for c in out["cases"]}
        assert by_id["tab-aut-19"]["status"] == "covered"
        assert "STATIC-ANALYSIS EVIDENCE" not in llm.calls[0]["user"]


class TestEvidenceInjection:
    def test_prompt_cites_the_real_orphaned_read(self):
        llm = FakeLLM(response={"cases": []})
        cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                 contract_findings=_findings())
        prompt = llm.calls[0]["user"]
        assert "STATIC-ANALYSIS EVIDENCE" in prompt
        assert "role" in prompt
        assert "services/auth_service/middleware.py" in prompt
        assert "services/auth_service/refresh.py" in prompt
        assert 'claims.get("role"' in prompt


class TestDeterministicCap:
    def test_covered_verdict_for_tab_aut_19_is_capped(self):
        """This reproduces the ACTUAL benchmark failure: the real Mind Map LLM had both
        tokens.py and middleware.py in evidence and still said 'covered' for TAB-AUT-19. The
        FakeLLM here simulates that exact (wrong) verdict; the cap must catch it regardless."""
        llm = FakeLLM(response={"cases": [
            {"test_case_id": "tab-aut-19", "status": "covered", "confidence": 0.9,
             "rationale": "require_role checks the token's role against allowed_roles",
             "files": ["services/auth_service/middleware.py"]}]})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                       contract_findings=_findings())
        c = {c["test_case_id"]: c for c in out["cases"]}["tab-aut-19"]
        assert c["status"] == "partial"
        assert c["needs_review"] is True
        assert c["downgraded_from"] == "covered"
        assert "contract_break_cap" in c
        assert "role" in c["contract_break_cap"]

    def test_covered_verdict_for_tab_aut_30_is_capped(self):
        llm = FakeLLM(response={"cases": [
            {"test_case_id": "tab-aut-30", "status": "covered", "confidence": 0.9,
             "rationale": "RBAC is implemented via require_role",
             "files": ["services/auth_service/middleware.py"]}]})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                       contract_findings=_findings())
        c = {c["test_case_id"]: c for c in out["cases"]}["tab-aut-30"]
        assert c["status"] == "partial"
        assert "contract_break_cap" in c

    def test_unrelated_case_is_not_capped(self):
        llm = FakeLLM(response={"cases": [
            {"test_case_id": "tab-aut-25", "status": "covered", "confidence": 0.9,
             "rationale": "login records an audit entry",
             "files": ["services/auth_service/tokens.py"]}]})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                       contract_findings=_findings())
        c = {c["test_case_id"]: c for c in out["cases"]}["tab-aut-25"]
        assert c["status"] == "covered"
        assert "contract_break_cap" not in c

    def test_uncovered_verdict_is_left_alone(self):
        llm = FakeLLM(response={"cases": [
            {"test_case_id": "tab-aut-19", "status": "uncovered", "confidence": 0.2,
             "rationale": "no matching code found", "files": []}]})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                       contract_findings=_findings())
        c = {c["test_case_id"]: c for c in out["cases"]}["tab-aut-19"]
        assert c["status"] == "uncovered"
        assert "contract_break_cap" not in c

    def test_contract_findings_considered_reported(self):
        llm = FakeLLM(response={"cases": []})
        out = cov.review_code_coverage(llm, "Authentication", "req", _cases(), _excerpts(),
                                       contract_findings=_findings())
        assert out.get("contract_findings_considered", 0) >= 1
