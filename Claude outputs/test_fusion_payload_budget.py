"""Regression coverage for the Fusion prompt-size safeguard.

Live incident this closes: a project with 173 accumulated test cases produced a
232,629-token Fusion prompt against gpt-4o-mini's 128K limit, and the generation job
failed outright. Root cause was that _project_existing_tests()'s output (up to 200
project-wide cases, each up to 8 steps) was serialized into build_fusion_pass_prompt()
with only a fixed ITEM-COUNT cap (prompt_builder's existing `project_existing_tests[:100]`
slice) -- not a safe proxy for prompt SIZE, since step count and step-text length vary
per case.

Two independent, complementary fixes are exercised here:
  1. _bound_project_tests_for_fusion() bounds the payload by actual serialized
     character size (not count) BEFORE it ever reaches the prompt builder, so an
     oversized project no longer produces an oversized request in the first place.
  2. The Fusion LLM call is now wrapped so that if it fails anyway (a budget
     miscalculation, a transient provider error, anything), generation degrades to "no
     inheritance candidates this run" instead of crashing the whole job.

Nothing about the four-category RAG architecture, the embedding abstraction, or the
grounding guard is touched by any of this -- this file only exercises the Fusion pass.
"""
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../app")))

from testgen.service import (  # noqa: E402
    _FUSION_EXISTING_TESTS_CHAR_BUDGET,
    _bound_project_tests_for_fusion,
    _case_relevance_score,
    generate_fresh_testcases_pipeline,
)
from tests.test_generation_pipeline import FakeEmbedder, FakeLLM, FakeStore  # noqa: E402


# --------------------------------------------------------------------------------
# Part 1: pure unit tests on the budgeting function itself.
# --------------------------------------------------------------------------------

def _big_case(index, steps=8, step_len=220, title="Existing project case"):
    action = ("Perform a documented setup step with substantial descriptive detail. " * 4)[:step_len]
    expected = ("Verify a specific, detailed, previously-established outcome occurs. " * 4)[:step_len]
    return {
        "id": f"proj-case-{index}",
        "reference_key": f"proj-case-{index}",
        "title": f"{title} {index}",
        "type": "functional",
        "priority": "P2",
        "identity_hash": f"hash-{index}",
        "test_slug": f"slug-{index}",
        "steps": [{"content": action, "expectedResult": expected} for _ in range(steps)],
    }


class BoundProjectTestsUnitTests(unittest.TestCase):
    def test_a_small_project_is_returned_completely_unchanged(self):
        """No truncation, no reordering, no new object identity -- Fusion behavior for
        a typical/small project must be byte-identical to before this change."""
        cases = [_big_case(i, steps=2, step_len=40) for i in range(5)]
        bounded, dropped = _bound_project_tests_for_fusion(cases, "Create order")
        self.assertIs(bounded, cases)
        self.assertEqual(0, dropped)

    def test_an_oversized_project_is_trimmed_below_the_budget(self):
        cases = [_big_case(i) for i in range(180)]
        self.assertGreater(
            len(json.dumps(cases, indent=2)), _FUSION_EXISTING_TESTS_CHAR_BUDGET * 5,
            "fixture sanity check: 180 eight-step cases must genuinely exceed the budget",
        )
        bounded, dropped = _bound_project_tests_for_fusion(cases, "Create order")
        self.assertLessEqual(len(json.dumps(bounded, indent=2)), _FUSION_EXISTING_TESTS_CHAR_BUDGET)
        self.assertGreater(dropped, 0)
        self.assertEqual(180, len(bounded) + dropped)

    def test_trimming_keeps_at_least_some_cases_not_zero(self):
        """The budget must not be so tight it discards everything -- Fusion must
        remain useful, per the explicit 'preserve enough context to remain useful'
        requirement."""
        cases = [_big_case(i) for i in range(180)]
        bounded, _ = _bound_project_tests_for_fusion(cases, "Create order")
        self.assertGreater(len(bounded), 0)

    def test_relevant_cases_are_preferred_when_not_everything_fits(self):
        """When forced to drop cases, the ones whose title actually overlaps the
        current feature's own text are the ones kept."""
        relevant = [
            _big_case(i, title="Create order validates the customer payment method")
            for i in range(5)
        ]
        noise = [_big_case(100 + i, title="Unrelated warehouse inventory audit case") for i in range(60)]
        cases = noise[:30] + relevant + noise[30:]
        bounded, dropped = _bound_project_tests_for_fusion(cases, "Create order customer payment")
        self.assertGreater(dropped, 0, "fixture sanity check: truncation must actually occur")
        kept_ids = {case["id"] for case in bounded}
        for case in relevant:
            self.assertIn(case["id"], kept_ids, "a case genuinely about this feature must survive")

    def test_kept_cases_preserve_their_original_relative_order(self):
        """Reordering by relevance internally must not leak into the prompt's case
        order -- keep it predictable/readable, matching pre-existing behavior."""
        cases = [_big_case(i, steps=1, step_len=30) for i in range(10)]
        bounded, dropped = _bound_project_tests_for_fusion(cases, "irrelevant", budget_chars=800)
        self.assertGreater(dropped, 0)
        ids = [case["id"] for case in bounded]
        self.assertEqual(ids, sorted(ids, key=lambda cid: cases.index(next(c for c in cases if c["id"] == cid))))

    def test_relevance_score_is_pure_token_overlap_no_llm_no_embedding(self):
        self.assertEqual(
            3, _case_relevance_score({"title": "Create order rejects invalid payment"},
                                      {"create", "order", "payment"}),
        )
        self.assertEqual(0, _case_relevance_score({"title": "Unrelated case"}, set()))

    def test_empty_project_tests_is_a_no_op(self):
        bounded, dropped = _bound_project_tests_for_fusion([], "Create order")
        self.assertEqual([], bounded)
        self.assertEqual(0, dropped)


# --------------------------------------------------------------------------------
# Part 2: end-to-end through generate_fresh_testcases_pipeline(), reproducing the live
# incident's shape with a fake LLM that simulates a real provider's context-length
# rejection when the prompt it actually receives is too large.
# --------------------------------------------------------------------------------

class OversizedProjectStore(FakeStore):
    """A project with many accumulated test cases, mirroring the live incident's shape
    (173 project-wide cases). get_case()/list_test_cases() are the two calls
    _project_existing_tests() makes; both are overridden here to serve from an
    in-memory pool sized well past what the budget allows through unfiltered."""

    def __init__(self, num_cases=180, **kwargs):
        super().__init__(**kwargs)
        self._project_cases = {f"proj-case-{i}": _big_case(i) for i in range(num_cases)}

    def list_test_cases(self, **kwargs):
        return {"items": [{"id": cid} for cid in self._project_cases]}

    def get_case(self, case_id):
        return self._project_cases.get(case_id)


# A conservative stand-in for "a real provider's context limit was exceeded". Set well
# above what a bounded Fusion prompt should ever reach (the cases block alone is capped
# at _FUSION_EXISTING_TESTS_CHAR_BUDGET=40,000 chars; FakeStore's PRD/siblings/graph
# content is a few KB at most) and well below what 180 unbounded eight-step cases
# produce (~380,000+ characters for the cases block alone) -- so this line is a genuine
# discriminator between "the fix bounded the request" and "it didn't".
_SIMULATED_PROVIDER_CONTEXT_LIMIT_CHARS = 150_000


class ContextLimitEnforcingLLM(FakeLLM):
    """Behaves exactly like FakeLLM for every call except Fusion, where it simulates a
    real provider rejecting an oversized prompt -- the actual failure mode from the
    live incident (a 232,629-token request against a 128K-token model)."""

    def __init__(self):
        self.fusion_prompt_sizes = []

    def _raw_chat(self, system, user, num_ctx, temperature, max_tokens, timeout_seconds=None):
        if "Analyze Cross-Feature Overlap" in user:
            self.fusion_prompt_sizes.append(len(user))
            if len(user) > _SIMULATED_PROVIDER_CONTEXT_LIMIT_CHARS:
                raise RuntimeError(
                    "context_length_exceeded: this model's maximum context length is "
                    "exceeded by the messages provided"
                )
        import json as _json
        return _json.dumps(self.chat_json(system, user))


def _run(store, llm, **params):
    return generate_fresh_testcases_pipeline(
        store, llm, FakeEmbedder(),
        {"feature_id": "feature-1", "total": 10, **params},
    )


class FusionDoesNotCrashOnOversizedProjectsTests(unittest.TestCase):
    def test_an_oversized_project_no_longer_exceeds_the_simulated_provider_limit(self):
        """The core regression: the same shape of project that broke a real 128K-token
        model live must now produce a Fusion request safely under that kind of limit."""
        store, llm = OversizedProjectStore(num_cases=180), ContextLimitEnforcingLLM()
        result = _run(store, llm)
        self.assertEqual(1, len(llm.fusion_prompt_sizes))
        self.assertLess(llm.fusion_prompt_sizes[0], _SIMULATED_PROVIDER_CONTEXT_LIMIT_CHARS)
        self.assertGreater(result["cases_new"] + result["cases_reused"], 0)
        self.assertEqual([], [e for e in result["errors"] if "Fusion" in e])

    def test_the_truncation_is_reported_on_the_job_result(self):
        store, llm = OversizedProjectStore(num_cases=180), ContextLimitEnforcingLLM()
        result = _run(store, llm)
        self.assertGreater(result.get("fusion_context_truncated", 0), 0)
        self.assertTrue(
            any(w.startswith("fusion:") for w in result.get("warnings", [])),
            "an empty/reduced Fusion input must be explained, not silent",
        )

    def test_a_small_project_reports_no_truncation(self):
        store, llm = OversizedProjectStore(num_cases=3), ContextLimitEnforcingLLM()
        result = _run(store, llm)
        self.assertNotIn("fusion_context_truncated", result)
        self.assertFalse(any(w.startswith("fusion:") for w in result.get("warnings", [])))

    def test_generation_completes_even_if_the_fusion_call_still_fails(self):
        """Defense in depth: even a Fusion failure unrelated to size (or a budget
        miscalculation) must degrade instead of crashing the whole job."""
        class AlwaysFailingFusionLLM(FakeLLM):
            def _raw_chat(self, system, user, num_ctx, temperature, max_tokens, timeout_seconds=None):
                if "Analyze Cross-Feature Overlap" in user:
                    raise RuntimeError("simulated transient provider error")
                import json as _json
                return _json_dumps_via_parent(self, system, user)

        def _json_dumps_via_parent(self, system, user):
            import json as _json
            return _json.dumps(FakeLLM.chat_json(self, system, user))

        store = OversizedProjectStore(num_cases=3)
        result = _run(store, AlwaysFailingFusionLLM())
        self.assertGreater(result["cases_new"] + result["cases_reused"], 0)
        self.assertTrue(any("Fusion pass failed" in e for e in result["errors"]))
        self.assertEqual(0, result["inherited_reused"])
        self.assertEqual(0, result["inherited_rebuilt"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
