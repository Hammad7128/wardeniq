"""Tests for the `repo_files` wiring added to `coverage.py::verify_pr_implementation` —
the second half of the Phase 1 cross-file dependency fix (the first half, the deterministic
`contract_break` tier in `grounding.match_commit_changes`, is covered by
tests/test_grounding_contract_tier.py and tests/test_contracts_full_suite_false_positives.py).

Uses the SAME real PR #9 (AUTH-007) fixture data pulled from the benchmark's actual git
history — nothing synthetic. A `FakeLLM` (see tests/conftest.py) stands in for the real
model so these tests exercise the deterministic evidence-injection and cap logic in
isolation, without requiring live LLM credentials (none are available in this sandbox).

TAB-AUT-19's steps below are the REAL generated step text (from an actual manual PR #9 run),
not a title-only placeholder — a title-only version of this case (no mention of "role") used
to pass only via an incidental collision on a consumer's fallback-default literal, which has
since been fixed (see grounding._mask_fallback_default). The real steps mention "role" directly,
which is what should — and does — carry the match now.
"""
import os

from conftest import FakeLLM

import coverage as cov

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


def _prod_files():
    return [{"filename": "services/auth_service/tokens.py", "status": "modified",
             "additions": 2, "deletions": 2, "patch": _read("pr9_tokens.patch")}]


def _repo_files():
    return [
        {"path": "services/auth_service/middleware.py", "text": _read("middleware.py.txt")},
        {"path": "services/auth_service/refresh.py", "text": _read("refresh.py.txt")},
        {"path": "services/auth_service/driver_only.py", "text": _read("driver_only.py.txt")},
        {"path": "services/auth_service/app.py", "text": _read("app.py.txt")},
        {"path": "services/auth_service/audit_log.py", "text": _read("audit_log.py.txt")},
    ]


def _cases():
    return [
        {"id": "tab-aut-19", "title": "Driver-Only Endpoint Rejects Non-Driver Tokens",
         "type": "functional", "steps": [
             {"action": "A user with 'rider' role logs in and obtains an access token.",
              "expected": "System issues a valid access token with 'rider' role."},
             {"action": "The user attempts to access a protected endpoint marked as "
                        "'driver-only' using their 'rider' access token.",
              "expected": "The protected endpoint's middleware processes the request."},
         ]},
        {"id": "tab-aut-30", "title": "Role-Based Access Control for Driver-Only Endpoint",
         "type": "functional", "steps": [{"action": "Role-Based Access Control for Driver-Only Endpoint",
                                          "expected": "behaves as titled"}]},
        {"id": "tab-aut-26", "title": "Successful User Login and Token Issuance",
         "type": "functional", "steps": [{"action": "Successful User Login and Token Issuance",
                                          "expected": "behaves as titled"}]},
    ]


class TestBackwardCompatibility:
    def test_omitting_repo_files_is_unchanged(self):
        """No repo_files -> no evidence block, no contract_breaks_considered key at all —
        exact prior behaviour, confirming the new parameter is truly optional."""
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-19", "status": "covered", "confidence": 0.9,
             "rationale": "issue_token_pair changed", "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases())
        assert "contract_breaks_considered" not in out
        assert out["covered"][0]["status"] == "covered"       # no cap applied
        assert "CROSS-FILE DEPENDENCY EVIDENCE" not in llm.calls[0]["user"]


class TestEvidenceInjection:
    def test_prompt_cites_real_consumers(self):
        """With repo_files supplied, the prompt handed to the LLM must contain a grounded,
        cited evidence block naming the real consumer files/lines and both key names —
        not vague prose."""
        llm = FakeLLM(response={"covered": []})
        cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                     _prod_files(), _cases(), repo_files=_repo_files())
        prompt = llm.calls[0]["user"]
        assert "CROSS-FILE DEPENDENCY EVIDENCE" in prompt
        assert "role" in prompt and "user_role" in prompt
        assert "services/auth_service/middleware.py" in prompt
        assert "services/auth_service/refresh.py" in prompt
        # Cited line content must be the REAL snippet, not a fabricated summary.
        assert 'claims.get("role"' in prompt


class TestDeterministicCap:
    def test_covered_verdict_is_capped_when_a_relevant_break_is_unresolved(self):
        """Even if the (fake, simulating a naive/wrong) LLM says 'covered' for TAB-AUT-19,
        the deterministic cap must force it down to 'partial' and flag for review, because
        a real, cited consumer (middleware.py) still reads the OLD contract and was not
        part of this PR's diff. This must hold regardless of what the LLM said — the whole
        point of the cap is that it does not trust the LLM on this specific question."""
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-19", "status": "covered", "confidence": 0.95,
             "rationale": "issue_token_pair now sets user_role and middleware enforces it",
             "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases(), repo_files=_repo_files())
        c = out["covered"][0]
        assert c["test_case_id"] == "tab-aut-19"
        assert c["status"] == "partial"
        assert c["needs_review"] is True
        assert "contract_break_cap" in c
        assert "middleware.py" in c["contract_break_cap"]
        assert "role" in c["contract_break_cap"]

    def test_covered_verdict_for_tab_aut_30_is_also_capped(self):
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-30", "status": "covered", "confidence": 0.9,
             "rationale": "RBAC implemented", "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases(), repo_files=_repo_files())
        c = out["covered"][0]
        assert c["status"] == "partial"
        assert "contract_break_cap" in c

    def test_unrelated_case_is_not_capped(self):
        """The cap must be precise, not a blanket downgrade of every 'covered' verdict in a
        PR that happens to have SOME contract break somewhere — an unrelated case (no shared
        distinctive token with the break) must be left exactly as the LLM (and normal
        grounding) determined it."""
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-26", "status": "covered", "confidence": 0.9,
             "rationale": "issue_token_pair issues tokens on login",
             "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases(), repo_files=_repo_files())
        c = out["covered"][0]
        assert c["test_case_id"] == "tab-aut-26"
        assert c["status"] == "covered"
        assert "contract_break_cap" not in c

    def test_partial_verdict_is_left_alone_by_the_cap(self):
        """The cap only ever pulls DOWN a 'covered' claim; it must not touch a verdict that
        was already 'partial' (nothing to cap, and no double-penalty)."""
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-19", "status": "partial", "confidence": 0.5,
             "rationale": "touches the area", "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases(), repo_files=_repo_files())
        c = out["covered"][0]
        assert c["status"] == "partial"
        assert "contract_break_cap" not in c

    def test_contract_breaks_considered_reported(self):
        llm = FakeLLM(response={"covered": []})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "rename role"},
                                           _prod_files(), _cases(), repo_files=_repo_files())
        assert out.get("contract_breaks_considered", 0) >= 1


class TestDeterministicLayerNeverBreaksTheVerifier:
    def test_garbage_repo_files_does_not_raise(self):
        """contracts.build_contract_breaks must be defensively wrapped: malformed repo_files
        must degrade to 'no evidence found', never crash the whole verifier."""
        llm = FakeLLM(response={"covered": [
            {"test_case_id": "tab-aut-19", "status": "covered", "confidence": 0.9,
             "rationale": "ok", "files": ["services/auth_service/tokens.py"]}]})
        out = cov.verify_pr_implementation(llm, {"number": 9, "title": "x"}, _prod_files(),
                                           _cases(), repo_files=[{"path": None, "text": None}])
        assert out["covered"][0]["test_case_id"] == "tab-aut-19"
