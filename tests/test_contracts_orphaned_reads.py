"""Tests for `contracts.find_orphaned_contract_reads` — the SNAPSHOT-ONLY companion to
`build_contract_breaks`, added specifically for Mind Map (`coverage.review_code_coverage` /
main.py's `_codeanalysis_worker`).

Why this exists: the benchmark evidence (raw-results/wardeniq/
auth-mindmap-branch4-refactor-auth-token-claim-naming.md) shows Mind Map's AUTH-007 miss was
NOT a missing-evidence problem like PR Code Coverage's and Code Analysis's — both tokens.py
(the producer) and middleware.py (the consumer) were already in the evidence Mind Map's LLM
reviewed, and it still failed to connect "this key stopped being written" to "this code still
reads it". Mind Map also has no diff at all to work from (it reviews a single current
snapshot), so `build_contract_breaks` (which needs a PR diff) cannot apply. This module
detects the same class of bug from a snapshot alone: a `.get(KEY, ...)` read whose KEY is
never written by anything in the current codebase is suspicious regardless of *how* it came to
be orphaned (rename, removal, typo) — no diff required.

All fixture data is real, pulled directly from the benchmark's actual git history via
`git show` — nothing synthetic, per this pilot's testing standard — EXCEPT
`TestExternalReceiversExcluded`, which is a narrow, explicitly-labelled unit test of one
specific exclusion rule (env vars / HTTP headers are not local contracts) and makes no claim
about benchmark behaviour.

Beyond what's encoded here, this detector was also manually validated (see
WARDENIQ_CROSS_FILE_BEFORE_AFTER.md for the full record) against the ENTIRE real taxi-app
repository at 8 different real commits/branches spanning all 4 auth-pilot branches plus 5
unrelated feature branches (promo pricing, driver-status caching, payment sandbox seeding,
payment capture flow, mobile audience fix) — every one of those real, unmodified snapshots
produced ZERO findings, and only the actual post-rename AUTH-007 snapshot produced the one
correct finding. That full-repo sweep is not re-encoded here as an automated test because it
depends on the benchmark's separate git checkout (`/tmp/bench/taxi-app`) rather than a
committed fixture, but the result is part of this fix's verification record.
"""
import os

import contracts

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


def _snapshot(tokens_variant):
    return [
        {"path": "services/auth_service/middleware.py", "text": _read("middleware.py.txt")},
        {"path": "services/auth_service/refresh.py", "text": _read("refresh.py.txt")},
        {"path": "services/auth_service/driver_only.py", "text": _read("driver_only.py.txt")},
        {"path": "services/auth_service/app.py", "text": _read("app.py.txt")},
        {"path": "services/auth_service/audit_log.py", "text": _read("audit_log.py.txt")},
        {"path": "services/auth_service/tokens.py", "text": _read(tokens_variant)},
    ]


class TestOrphanedReadDetectedPostRename:
    """The real, post-PR9 snapshot: tokens.py writes `user_role`, but middleware.py and
    refresh.py still read `role` — exactly the AUTH-007 scenario, from a snapshot alone."""

    def test_finds_exactly_one_orphaned_key(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_after.py.txt"))
        assert len(findings) == 1
        assert findings[0]["old_key"] == "role"
        assert findings[0]["change_type"] == "orphaned_read"

    def test_cites_both_real_consumers(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_after.py.txt"))
        consumer_files = {c["file"] for c in findings[0]["consumers"]}
        assert consumer_files == {"services/auth_service/middleware.py",
                                  "services/auth_service/refresh.py"}

    def test_suggests_the_real_rename_target_without_asserting_it(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_after.py.txt"))
        assert findings[0]["suggested_replacement_key"] == "user_role"
        # A snapshot alone cannot CONFIRM a rename (only a diff can) — new_key must stay None
        # so downstream callers never treat a fuzzy same-repo guess as a certain fact.
        assert findings[0]["new_key"] is None

    def test_reason_is_explainable(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_after.py.txt"))
        reason = findings[0]["reason"]
        assert "role" in reason and "user_role" in reason and "WRITES" in reason

    def test_producer_is_not_flagged_as_its_own_consumer(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_after.py.txt"))
        consumer_files = {c["file"] for c in findings[0]["consumers"]}
        assert "services/auth_service/tokens.py" not in consumer_files


class TestNoFalsePositiveBeforeTheRename:
    """Negative control: the SAME consumer files, against the tokens.py version from BEFORE
    PR #9 (real git history, branch `feat/auth-refresh-tokens` @ 1dcacb1), where `role` is
    still actually written. The detector must recognise this is fine — this is what proves it
    responds to the real state of the code rather than reflexively flagging `role`."""

    def test_zero_findings_when_the_key_is_still_written(self):
        findings = contracts.find_orphaned_contract_reads(_snapshot("tokens_before.py.txt"))
        assert findings == []


class TestExternalReceiversExcluded:
    """Narrow unit test of one exclusion rule: environment/HTTP-layer `.get(...)` calls are not
    local application contracts, so "nothing in this repo writes that key" is the expected,
    unremarkable case for them — flagging it would be noise, not a finding. This fixture is a
    small inline snippet built to exercise the rule directly; it makes no claim about the real
    benchmark's behaviour (which is already covered by the real-fixture tests above, and none
    of the real snapshot sweeps hit this rule since the real code's genuine env/header reads
    were already correctly excluded — this test isolates WHY)."""

    def test_environ_get_not_flagged(self):
        text = (
            "import os\n"
            "def handler():\n"
            "    key = os.environ.get('SOME_UNWRITTEN_CONFIG_KEY')\n"
            "    return key\n"
        )
        findings = contracts.find_orphaned_contract_reads(
            [{"path": "app/config.py", "text": text}])
        assert findings == []

    def test_request_headers_get_not_flagged(self):
        text = (
            "def handler(request):\n"
            "    token = request.headers.get('authorization_custom_header')\n"
            "    return token\n"
        )
        findings = contracts.find_orphaned_contract_reads(
            [{"path": "app/handler.py", "text": text}])
        assert findings == []

    def test_genuinely_local_orphaned_key_is_still_flagged_alongside_external_reads(self):
        """The exclusion is narrow (receiver-based), not a blanket suppression once ANY
        external read appears in the same file — a real local orphaned key must still surface."""
        text = (
            "import os\n"
            "def handler(request):\n"
            "    cfg = os.environ.get('SOME_UNWRITTEN_CONFIG_KEY')\n"
            "    claims = decode(request)\n"
            "    role = claims.get('totally_unwritten_local_key')\n"
            "    return cfg, role\n"
        )
        findings = contracts.find_orphaned_contract_reads(
            [{"path": "app/handler.py", "text": text}])
        assert len(findings) == 1
        assert findings[0]["old_key"] == "totally_unwritten_local_key"
