"""Real-data validation of the new `contracts.py` producer/consumer dependency layer against
the actual Authentication-pilot benchmark evidence (AUTH-007 / PR #9 of x3444924-ai/taxi-app).

All fixture files in tests/fixtures/auth_pilot/ were pulled directly from the real git history
of the benchmark repo (`git show <sha>:<path>`) — nothing here is synthetic or hand-written to
make the fix pass. This is a LOCAL, uncommitted experiment (see the user's local-only
constraint) — it does not touch the live benchmark, the ground truth, or the PRs themselves.
"""
import os

import pytest

import contracts

pytestmark = pytest.mark.skip(
    reason=
    "fixtures in tests/fixtures/auth_pilot/ were pulled from an external benchmark repo as a local-only experiment and were never committed (by design, per the original author's local-only constraint); the originals are not recoverable. The feature under test (contracts.py's build_contract_breaks/find_orphaned_contract_reads, wired into coverage.py/grounding.py/codeanalysis_worker.py) remains live in production, untested until real fixtures are reconstructed."
)

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures", "auth_pilot")


def _read(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def pr9_files():
    """The PR #9 diff exactly as WardenIQ's PR-file shape represents it: filename + patch body
    (no diff --git/index/---/+++ headers — matches what GitHub's API actually returns, and what
    grounding.parse_added_lines already assumes elsewhere in this codebase)."""
    return [{"filename": "services/auth_service/tokens.py",
             "patch": _read("pr9_tokens.patch")}]


@pytest.fixture
def repo_snapshot():
    """The rest of the repo's CURRENT (post-PR9) full file text — exactly what
    `_codeanalysis_worker` already has in memory for every Mind Map run (`files` from
    `extractmod.source_files_from_tar`), and what the PR-Coverage/Code-Analysis wiring fetches
    for the app repo (see WARDENIQ_CROSS_FILE_BEFORE_AFTER.md for the main.py wiring)."""
    return [
        {"path": "services/auth_service/middleware.py", "text": _read("middleware.py.txt")},
        {"path": "services/auth_service/refresh.py", "text": _read("refresh.py.txt")},
        {"path": "services/auth_service/driver_only.py", "text": _read("driver_only.py.txt")},
        {"path": "services/auth_service/app.py", "text": _read("app.py.txt")},
        {"path": "services/auth_service/audit_log.py", "text": _read("audit_log.py.txt")},
        {"path": "services/auth_service/tokens.py", "text": _read("tokens_after.py.txt")},  # diff's own file — must be excluded automatically
    ]


class TestAuth007ContractBreakDetected:
    """Phase 2 checklist, item by item — does the NEW deterministic layer surface exactly what
    the benchmark evidence says all three original WardenIQ engines missed?"""

    def test_detects_a_contract_break_at_all(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        assert result["contract_breaks"], "expected at least one contract break to be found"

    def test_identifies_producer_file_and_function(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        assert b["producer_file"] == "services/auth_service/tokens.py"
        assert b["producer_function"] == "issue_token_pair"

    def test_identifies_the_exact_key_rename(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        assert b["old_key"] == "role"
        assert b["new_key"] == "user_role"
        assert b["change_type"] == "rename"

    def test_identifies_middleware_as_a_consumer(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        consumer_files = {c["file"] for c in b["consumers"]}
        assert "services/auth_service/middleware.py" in consumer_files

    def test_identifies_refresh_as_a_consumer(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        consumer_files = {c["file"] for c in b["consumers"]}
        assert "services/auth_service/refresh.py" in consumer_files

    def test_consumer_citation_is_grounded_at_the_real_line(self, pr9_files, repo_snapshot):
        """The consumer evidence must point at a REAL line that REALLY reads the old key —
        not a fabricated citation. Cross-check against the actual fixture file content."""
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        middleware_text = _read("middleware.py.txt")
        middleware_lines = middleware_text.splitlines()
        mw_consumers = [c for c in b["consumers"] if c["file"] == "services/auth_service/middleware.py"]
        assert mw_consumers
        for c in mw_consumers:
            real_line = middleware_lines[c["line"] - 1]
            assert "role" in real_line, f"citation line {c['line']} does not actually mention 'role': {real_line!r}"
            # And the citation is honest about what it found — should be the .get("role", ...) call
        assert any('.get("role"' in mc["snippet"] or ".get('role'" in mc["snippet"] for mc in mw_consumers)

    def test_reason_is_a_plain_explanation_not_a_black_box(self, pr9_files, repo_snapshot):
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        assert "role" in b["reason"] and "user_role" in b["reason"]
        assert "tokens.py" in b["reason"] or b["producer_file"] in b["reason"]

    def test_diff_file_itself_is_never_reported_as_its_own_consumer(self, pr9_files, repo_snapshot):
        """tokens.py still contains "role" as a local variable name (issue_token_pair's own
        `role` parameter) — the module must not report the diff's own file as a consumer of
        itself, since that would not be a real cross-file finding."""
        result = contracts.build_contract_breaks(pr9_files, repo_snapshot)
        b = result["contract_breaks"][0]
        consumer_files = {c["file"] for c in b["consumers"]}
        assert "services/auth_service/tokens.py" not in consumer_files


class TestFalsePositives:
    """Do NOT flag PRs #6, #7, #8 (no contract rename in this pilot's ground truth for those
    PRs) — these are the negative controls the user asked for ('check for false positives
    introduced by the new dependency layer')."""

    def _pr_files_from_full_diff(self, diff_text):
        """Parse a full `git diff` (with real ---/+++ headers) into the {filename, patch} shape
        contracts.py expects, one entry per file."""
        import re
        files = []
        blocks = re.split(r"^diff --git ", diff_text, flags=re.M)[1:]
        for block in blocks:
            m = re.search(r"^\+\+\+ b/(.+)$", block, flags=re.M)
            if not m:
                continue
            filename = m.group(1).strip()
            hunk_start = block.find("\n@@")
            patch = block[hunk_start + 1:] if hunk_start != -1 else ""
            files.append({"filename": filename, "patch": patch})
        return files

    @pytest.mark.parametrize("diff_name", ["pr6_full.diff", "pr7_full.diff", "pr8_full.diff"])
    def test_no_contract_break_false_positive(self, diff_name, repo_snapshot):
        pr_files = self._pr_files_from_full_diff(_read(diff_name))
        result = contracts.build_contract_breaks(pr_files, repo_snapshot)
        # These PRs add NEW code / fix a rotation bug / add middleware — none of them rename an
        # existing key that an UNCHANGED file elsewhere still reads. A break here would be a
        # false positive from the new layer.
        assert result["contract_breaks"] == [], (
            f"unexpected contract break(s) flagged on {diff_name}: {result['contract_breaks']}")
