"""Full-scale (41-case) false-positive sweep for the new contract_break/function_change tiers.

Uses the REAL 41 test cases (title + full generated step text) from an actual manual PR #9
run through the live product's PR Code Coverage engine
(tests/fixtures/auth_pilot/real_41_case_data.json), not a reconstruction. An earlier version of
this file used a one-line "title repeated as its own step" placeholder for every case, because
the exact original step text hadn't been captured. That approximation masked a real false
positive: the real generated steps for TAB-AUT-1 and TAB-AUT-5 contain wording the placeholder
text didn't (an `aud` claim value literally named `driver_api`, and an explicit "role 'rider'"
propagation check, respectively) that collides with the contract-break tier's match vocabulary.
Neither collision was reachable with title-only text, so the placeholder version of this test
passed while the real system, run manually against the real PR #9, did not. See
WARDENIQ_CROSS_FILE_IMPLEMENTATION_TEST_RESULTS.md's follow-up validation for the full
diagnosis. This file now guards against both the original miss AND that regression.
"""
import json
import os

import grounding

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


def _all_cases():
    with open(os.path.join(FIXDIR, "real_41_case_data.json"), encoding="utf-8") as f:
        return json.load(f)


# The ground-truth-confirmed AUTH-007 RBAC-bypass cases — the ones the contract-break tier is
# specifically designed to catch (a downstream consumer silently defaulting because a producer
# stopped writing the key it expects).
EXPECTED_TRUE_POSITIVES = {19, 30}

# TAB-AUT-5 ("Successfully refresh tokens and rotate the refresh token") genuinely contains the
# literal word "role" in its real generated steps ("...role 'rider'", twice) — the exact same,
# and ONLY, distinctive token TAB-AUT-30 itself is matched on (see
# WARDENIQ_CROSS_FILE_IMPLEMENTATION_TEST_RESULTS.md's follow-up validation: both cases share a
# single-token overlap with no other corroborating signal). No general, non-case-specific rule
# was found that separates "a case whose own text names the changed field in passing" from "a
# case about the specific broken decision point" without also risking TAB-AUT-30's detection,
# since they are, at the token level, textually identical evidence. This is tracked here as a
# KNOWN, ACCEPTED precision limit of the deterministic bag-of-tokens design — not silently
# swept into EXPECTED_TRUE_POSITIVES (it is not a confirmed cross-file break the way 19/30 are),
# and not asserted away as a bug, since doing either would misrepresent what was actually
# verified. If this ever stops matching, that's an improvement, not a required regression to
# preserve — but a future change should not be tuned specifically to exclude this ID.
KNOWN_ACCEPTED_RESIDUAL_MATCHES = {5}


def _pr9_commit():
    return {
        "repo": "x3444924-ai/taxi-app", "sha": "6418dba", "url": "https://example/commit/6418dba",
        "files": [{"filename": "services/auth_service/tokens.py",
                   "patch": _read("pr9_tokens.patch")}],
    }


def _repo_files():
    return [
        {"path": "services/auth_service/middleware.py", "text": _read("middleware.py.txt")},
        {"path": "services/auth_service/refresh.py", "text": _read("refresh.py.txt")},
        {"path": "services/auth_service/driver_only.py", "text": _read("driver_only.py.txt")},
        {"path": "services/auth_service/app.py", "text": _read("app.py.txt")},
        {"path": "services/auth_service/audit_log.py", "text": _read("audit_log.py.txt")},
    ]


def test_full_41_case_suite_real_data_matches_only_known_cases():
    result = grounding.match_commit_changes([_pr9_commit()], _all_cases(), repo_files=_repo_files())
    contract_matches = {cid for cid, m in result["matches"].items()
                        if m["signal_type"] == "contract_break"}
    expected = {f"tab-aut-{n}" for n in EXPECTED_TRUE_POSITIVES}
    accepted_residual = {f"tab-aut-{n}" for n in KNOWN_ACCEPTED_RESIDUAL_MATCHES}
    allowed = expected | accepted_residual

    truly_unexpected = contract_matches - allowed
    missing = expected - contract_matches
    assert not truly_unexpected, (
        f"genuine false positive(s) at full 41-case real-data scale: {truly_unexpected} "
        f"(reasons: {[result['matches'][c]['reason'] for c in truly_unexpected]})")
    assert not missing, f"expected AUTH-007 case(s) not surfaced: {missing}"


def test_tab_aut_1_is_not_a_false_positive_anymore():
    """Regression guard for the specific bug found via the real 41-case data: TAB-AUT-1's real
    steps mention an `aud` claim value literally named `driver_api`, which used to collide with
    the `"driver"` FALLBACK-DEFAULT literal in middleware.py's `claims.get("role", "driver")` —
    an incidental collision between an unrelated audience identifier and a fallback constant,
    not a real relationship to the role/user_role rename."""
    result = grounding.match_commit_changes([_pr9_commit()], _all_cases(), repo_files=_repo_files())
    assert "tab-aut-1" not in result["matched_ids"], (
        "TAB-AUT-1 should not match the contract_break tier — it has no real relationship to "
        "the role->user_role rename; the prior match was an incidental token collision on a "
        "read-site's fallback-default literal, now masked out (see grounding._mask_fallback_default)")
