"""Integration-level test: does the new contract_break tier wired into
`grounding.match_commit_changes` actually surface TAB-AUT-19 / TAB-AUT-30 for the real PR #9
diff, using the real repo file contents pulled from the benchmark's git history?

TAB-AUT-19 and TAB-AUT-30 use the REAL generated step text (captured from an actual manual PR #9
run through the live product), not a reconstruction — an earlier "title repeated as its own
step" placeholder for TAB-AUT-19 (which never mentions "role", only "driver") happened to only
pass via an incidental token collision on a consumer's fallback-default literal that has since
been masked out as a real false-positive fix (see grounding._mask_fallback_default and
WARDENIQ_CROSS_FILE_IMPLEMENTATION_TEST_RESULTS.md's follow-up validation). The real TAB-AUT-19
steps independently mention "role" directly, which is what should — and does — carry the match.
The other 16 cases here remain reasonable title-based reconstructions (exact step text for them
wasn't needed to diagnose or fix the false positive), used only to exercise the domain-token
guard at a realistic suite scale.
"""
import os

import grounding

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


def _pr9_commit():
    with open(os.path.join(FIXDIR, "pr9_tokens.patch"), encoding="utf-8") as f:
        patch = f.read()
    return {
        "repo": "x3444924-ai/taxi-app", "sha": "6418dba", "url": "https://example/commit/6418dba",
        "files": [{"filename": "services/auth_service/tokens.py", "patch": patch}],
    }


def _repo_files():
    return [
        {"path": "services/auth_service/middleware.py", "text": _read("middleware.py.txt")},
        {"path": "services/auth_service/refresh.py", "text": _read("refresh.py.txt")},
        {"path": "services/auth_service/driver_only.py", "text": _read("driver_only.py.txt")},
        {"path": "services/auth_service/app.py", "text": _read("app.py.txt")},
        {"path": "services/auth_service/audit_log.py", "text": _read("audit_log.py.txt")},
    ]


def _cases():
    """A realistic-scale case list (18 of the real 41 titles captured in
    raw-results/wardeniq/auth-testcase-generation.md) so the SAME domain-token
    distinctiveness cutoff the real 41-case benchmark used is actually exercised — a 2-3
    case toy suite falls into `match_commit_changes`'s deliberate "small suites: every
    token counts" leniency clause and would make the guard look weaker than it really is
    at the benchmark's real scale. Steps are reasonable reconstructions (exact original step
    text wasn't captured in the evidence, only titles) used only to exercise tokenization."""
    titles = [
        ("tab-aut-2", "Reject refresh request with an expired refresh token"),
        ("tab-aut-5", "Successfully refresh tokens and rotate the refresh token"),
        ("tab-aut-10", "Ensure a phone number is provided before attempting to log in."),
        ("tab-aut-11", "Ensure the phone number is entered in a valid format."),
        ("tab-aut-12", "Ensure the one-time code is provided for authentication."),
        ("tab-aut-15", "Display a generic error message for a non-existent phone number, without revealing specifics."),
        ("tab-aut-19", "Driver-Only Endpoint Rejects Non-Driver Tokens"),
        ("tab-aut-20", "OTP Brute-Force Lockout After Multiple Failed Attempts"),
        ("tab-aut-21", "All Authentication Failures Return Generic Error Messages"),
        ("tab-aut-22", "Expired Access Tokens Are Rejected"),
        ("tab-aut-23", "Access Tokens with Invalid Issuer Claim Are Rejected"),
        ("tab-aut-25", "Successful Login Attempts Are Recorded in Audit Log"),
        ("tab-aut-26", "Successful User Login and Token Issuance"),
        ("tab-aut-29", "OTP Brute-Force Lockout Protection"),
        ("tab-aut-30", "Role-Based Access Control for Driver-Only Endpoint"),
        ("tab-aut-32", "Authentication service fails to start in production without USER_TOKEN_SIGNING_KEY"),
        ("tab-aut-33", "Payment service ensures idempotency for payment capture requests"),
        ("tab-aut-39", "Attempting Login with a Non-Existent Phone Number"),
    ]
    # Real generated steps for the two cases this test actually asserts on (TAB-AUT-19/30),
    # captured from an actual manual PR #9 run — see the module docstring.
    real_steps = {
        "tab-aut-19": [
            {"action": "A user with 'rider' role logs in and obtains an access token.",
             "expected": "System issues a valid access token with 'rider' role."},
            {"action": "The user attempts to access a protected endpoint marked as "
                       "'driver-only' using their 'rider' access token.",
             "expected": "The protected endpoint's middleware processes the request."},
        ],
        "tab-aut-30": [
            {"action": "User logs in successfully as a 'rider'.",
             "expected": "The described observable outcome occurs."},
            {"action": "User attempts to navigate to a UI section or trigger an action that "
                       "calls a 'driver-only' endpoint.",
             "expected": "The described observable outcome occurs."},
        ],
    }
    return [{"id": cid, "display_id": cid.upper().replace("TAB-AUT", "TAB-AUT"),
             "type": "functional", "title": title,
             "steps": real_steps.get(cid, [{"action": title, "expected": "behaves as titled"}])}
            for cid, title in titles]


class TestContractBreakTierSurfacesAuth007:
    def test_without_repo_files_reproduces_prior_behavior_and_misses_it(self):
        """Backward compatibility: omitting repo_files must reproduce the EXACT prior miss —
        this is the documented 'before' state from the benchmark evidence."""
        result = grounding.match_commit_changes([_pr9_commit()], _cases())
        assert "tab-aut-19" not in result["matched_ids"]
        assert "tab-aut-30" not in result["matched_ids"]

    def test_with_repo_files_surfaces_tab_aut_19(self):
        result = grounding.match_commit_changes([_pr9_commit()], _cases(), repo_files=_repo_files())
        assert "tab-aut-19" in result["matched_ids"], (
            "TAB-AUT-19 should now be surfaced via the contract_break tier")
        m = result["matches"]["tab-aut-19"]
        assert m["signal_type"] == "contract_break"
        assert m["risk"] == "high"

    def test_with_repo_files_surfaces_tab_aut_30(self):
        result = grounding.match_commit_changes([_pr9_commit()], _cases(), repo_files=_repo_files())
        assert "tab-aut-30" in result["matched_ids"]
        assert result["matches"]["tab-aut-30"]["signal_type"] == "contract_break"

    def test_evidence_cites_middleware_and_refresh(self):
        result = grounding.match_commit_changes([_pr9_commit()], _cases(), repo_files=_repo_files())
        for cid in ("tab-aut-19", "tab-aut-30"):
            evidence_files = {e["file"] for e in result["matches"][cid]["evidence"]}
            assert evidence_files & {"services/auth_service/middleware.py",
                                     "services/auth_service/refresh.py"}, (
                f"{cid} evidence should cite a real consumer file, got {evidence_files}")

    def test_reason_is_explainable(self):
        result = grounding.match_commit_changes([_pr9_commit()], _cases(), repo_files=_repo_files())
        reason = result["matches"]["tab-aut-19"]["reason"]
        assert "role" in reason and "user_role" in reason

    def test_negative_control_not_swept_in(self):
        """Cases with no plausible relationship to the RBAC/role rename must NOT be matched —
        proves the domain-token guard (reused from the existing symbol tier) still protects
        the contract-break tier from over-matching, at a realistic (18-case) suite size."""
        result = grounding.match_commit_changes([_pr9_commit()], _cases(), repo_files=_repo_files())
        unrelated = {"tab-aut-10", "tab-aut-11", "tab-aut-12", "tab-aut-15", "tab-aut-33", "tab-aut-39"}
        swept_in = unrelated & result["matched_ids"]
        assert not swept_in, f"unrelated case(s) incorrectly matched: {swept_in}"


class TestMaskFallbackDefault:
    """Unit tests for `grounding._mask_fallback_default`, added after a real 41-case manual PR
    #9 run showed TAB-AUT-1 ("...incorrect audience claims...", whose real steps mention an
    `aud` value literally named `driver_api`) falsely matching the contract_break tier — purely
    because `driver_api` tokenizes to include `driver`, which collided with the unrelated
    `"driver"` FALLBACK-DEFAULT literal in middleware.py's `claims.get("role", "driver")`. The
    fallback value is not part of the contract being read (only the key `"role"` is), so it's
    masked out before `literal_tokens()` runs — general by construction: it matches the
    `.get(key, default)` / `getattr(obj, key, default)` call SHAPE, not any specific key or
    value, so it behaves identically for any domain/key/fallback combination."""

    def test_get_with_default_is_masked(self):
        snippet = 'role = claims.get("role", "driver")'
        masked = grounding._mask_fallback_default(snippet)
        assert grounding.literal_tokens(masked) == {"role"}
        # the raw snippet itself (used for human/LLM-facing evidence text) is untouched
        assert "driver" in snippet

    def test_get_without_default_is_unchanged(self):
        snippet = 'new_pair = issue_token_pair(user_id=claims["sub"], role=claims.get("role"))'
        masked = grounding._mask_fallback_default(snippet)
        assert masked == snippet
        assert grounding.literal_tokens(masked) == {"role", "sub"}

    def test_getattr_with_default_is_masked(self):
        snippet = 'role = getattr(claims, "role", "driver")'
        masked = grounding._mask_fallback_default(snippet)
        assert grounding.literal_tokens(masked) == {"role"}

    def test_unrelated_default_value_no_longer_collides_with_case_text(self):
        """The exact TAB-AUT-1-shaped scenario at the unit level: a case whose only textual
        overlap with a contract-break's evidence is an unrelated compound identifier
        (`driver_api`) that happens to share a substring with a read-site's fallback constant
        (`"driver"`) — this must NOT be treated as a match."""
        case_tokens = grounding.domain_tokens({
            "title": "reject tokens with incorrect audience claims",
            "steps": [{"action": "obtain a token with aud claim set for driver_api",
                       "expected": "ok"}],
        })
        consumer_snippet = 'role = claims.get("role", "driver")'
        vocab = grounding.signal_tokens("role", "user_role") | grounding.literal_tokens(
            grounding._mask_fallback_default(consumer_snippet))
        assert not (case_tokens & vocab), (
            f"unrelated case tokens {case_tokens & vocab} should not overlap the masked vocab")
