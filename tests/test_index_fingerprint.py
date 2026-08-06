"""The code-index rules fingerprint must be stable ACROSS PROCESSES.

Why this file exists, and why it shells out
-------------------------------------------
`INDEX_RULES_FINGERPRINT` is stored next to a repo's code index so that changing the
test/spec exclusion rules invalidates stale indexes automatically. It was first built with
the builtin `hash()`, which CPython salts per interpreter (PEP 456) unless PYTHONHASHSEED
is pinned — and it is pinned nowhere in this repo. So the value changed on every restart,
the stored fingerprint never matched, and every Mind Map run re-fetched each repo tarball
and re-embedded every chunk. That silently defeated the incremental-reuse cache the check
was added to protect, and cost a full re-embed per run.

The trap: comparing the constant to itself *inside one process* passes even when the
implementation is broken, because the salt is fixed for the life of an interpreter. These
tests therefore spawn real subprocesses. An in-process assertion here would be worse than
no test at all, because it would look like coverage while proving nothing.
"""
import hashlib
import os
import subprocess
import sys

import coverage as cov

_APP_DIR = os.path.dirname(os.path.abspath(cov.__file__))
_PRINT_FINGERPRINT = (
    "import sys; sys.path.insert(0, %r); "
    "import coverage; print(coverage.INDEX_RULES_FINGERPRINT)" % _APP_DIR
)


def _fingerprint_from_fresh_process(env_extra=None):
    env = dict(os.environ)
    env.pop("PYTHONHASHSEED", None)          # never let the test pin what prod doesn't
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, "-c", _PRINT_FINGERPRINT],
                       capture_output=True, text=True, env=env, timeout=60)
    assert p.returncode == 0, f"subprocess failed: {p.stderr[-400:]}"
    return p.stdout.strip()


class TestFingerprintStability:
    def test_identical_across_three_fresh_interpreters(self):
        values = {_fingerprint_from_fresh_process() for _ in range(3)}
        assert len(values) == 1, (
            f"fingerprint is not process-stable: {values}. Every restart would invalidate "
            "every repo index and force a full re-fetch and re-embed.")

    def test_matches_the_value_in_this_process(self):
        # The running app compares its own constant against what a PREVIOUS process stored.
        assert _fingerprint_from_fresh_process() == cov.INDEX_RULES_FINGERPRINT

    def test_survives_a_randomised_hash_seed(self):
        # PYTHONHASHSEED=random is the default; make the hostile case explicit.
        a = _fingerprint_from_fresh_process({"PYTHONHASHSEED": "random"})
        b = _fingerprint_from_fresh_process({"PYTHONHASHSEED": "random"})
        assert a == b == cov.INDEX_RULES_FINGERPRINT

    def test_is_not_derived_from_builtin_hash(self):
        # Guards against a well-meaning revert to `hash()`, which would reintroduce the
        # bug invisibly. sha256 of the patterns is reproducible here; hash() is not.
        expected = "indexrules:" + hashlib.sha256(
            "\n".join(cov._INDEX_RULE_PATTERNS).encode("utf-8")).hexdigest()[:16]
        assert cov.INDEX_RULES_FINGERPRINT == expected


class TestFingerprintSemantics:
    def test_changes_when_the_exclusion_rules_change(self):
        """The whole point: different rules must produce a different fingerprint."""
        other = "indexrules:" + hashlib.sha256(
            "\n".join(cov._INDEX_RULE_PATTERNS + ("extra_rule",)).encode("utf-8")
        ).hexdigest()[:16]
        assert other != cov.INDEX_RULES_FINGERPRINT

    def test_every_registered_rule_actually_moves_the_fingerprint(self):
        """No input may be inert. Drop any one of them and the digest must change.

        A tuple element that makes no difference would be a rule the fingerprint only
        appears to cover — the failure mode is a silently-stale index, which is invisible
        precisely because everything keeps working.
        """
        rules = cov._INDEX_RULE_PATTERNS
        for i in range(len(rules)):
            without = rules[:i] + rules[i + 1:]
            digest = "indexrules:" + hashlib.sha256(
                "\n".join(without).encode("utf-8")).hexdigest()[:16]
            assert digest != cov.INDEX_RULES_FINGERPRINT, (
                f"rule #{i} contributes nothing to the fingerprint: {rules[i]!r}")

    def test_covers_every_rule_the_indexing_predicate_consults(self):
        """The bug this guards is 'added a rule, forgot to fingerprint it'.

        `is_non_implementation_file` is what main.py gates indexing on, so every pattern it
        reads must be an input here. Hashing only TEST_FILE_RE — as this did before the
        non-implementation rules landed — would leave every cached index valid after an
        exclusion-rule change, serving chunks filtered by rules nobody can see any more.
        That is the same defect class as the salted `hash()`, reached from the other side.
        """
        consulted = {
            cov.TEST_FILE_RE.pattern,
            cov.NON_IMPL_PATH_RE.pattern,
            cov._VALUE_CONSTRUCT_RE.pattern,
            cov._TYPE_ONLY_DECL_RE.pattern,
            cov._COMMENT_RE.pattern,
        }
        missing = consulted - set(cov._INDEX_RULE_PATTERNS)
        assert not missing, (
            "these patterns change what gets indexed but are not in the fingerprint, so "
            f"editing them will not invalidate stale indexes: {missing}")

    def test_is_a_short_printable_token(self):
        fp = cov.INDEX_RULES_FINGERPRINT
        assert fp.startswith("indexrules:")
        assert len(fp) < 40                       # goes into a Mongo doc, keep it small
        assert fp.strip() == fp and " " not in fp

    def test_differs_from_the_legacy_test_only_fingerprint(self):
        """Existing deployments must NOT read as up to date after this change.

        Indexes built before the non-implementation rules contain files those rules now
        exclude. If the fingerprint had kept its old form and value they would be reused
        as-is, and the stale corpus would keep supplying ineligible citations.
        """
        legacy = "testfilter:" + hashlib.sha256(
            cov.TEST_FILE_RE.pattern.encode("utf-8")).hexdigest()[:16]
        assert cov.INDEX_RULES_FINGERPRINT != legacy
