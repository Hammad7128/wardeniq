"""Reject prompt few-shot exemplars that generation copies as real test cases.

Issue #36: the bundled model can emit the event-host examples from
prompt_builder.py verbatim (or as hybrids) and persist them against an unrelated
feature such as password reset. The guard is deterministic and shared with the
prompt constants — it does not depend on a particular LLM.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from testgen.prompt_builder import (  # noqa: E402
    PROMPT_EXEMPLAR_E2E_INTENT,
    PROMPT_EXEMPLAR_E2E_PRECONDITIONS,
    PROMPT_EXEMPLAR_E2E_TITLE,
    PROMPT_EXEMPLAR_EDGE_TITLE,
    build_e2e_agent_prompt,
    is_prompt_exemplar_copy,
    filter_prompt_exemplar_copies,
)
from testgen.service import _case_has_source_grounding  # noqa: E402
from tests.test_rag_evidence_sufficiency import (  # noqa: E402
    ScenarioLLM,
    ScenarioStore,
    _run,
    _titles,
)


PASSWORD_RESET_TEXT = (
    "Registered users can request a password reset via email.\n"
    "The system sends a reset link to the address on file (FR-2).\n"
    "A reset token is valid for 30 minutes after it is issued.\n"
    "New passwords must be at least 12 characters and contain at least one letter.\n"
    "A single email address that requests 4 resets in 30 minutes is rate limited.\n"
    "Email addresses must be valid so the reset link reaches the correct inbox.\n"
    "There is no API surface and no UI mockup in this document.\n"
)

GROUNDED_RESET_TITLE = "Registered users can request a password reset via email"
HYBRID_E2E_TITLE = (
    "Host creates event then Email service fails on sending reset link — "
    "state remains consistent"
)


def _password_reset_store():
    return ScenarioStore(
        name="Password reset",
        summary="Let a registered user reset their password by email",
        text=PASSWORD_RESET_TEXT,
        chunks=[
            ("e2e", "Registered users can request a password reset via email."),
            ("business", "A reset token is valid for 30 minutes after it is issued."),
        ],
        business_context={"prd": {"requirements": [
            "Registered users can request a password reset via email.",
            "A reset token is valid for 30 minutes after it is issued.",
        ]}},
    )


class PromptExemplarUnitTests(unittest.TestCase):
    def test_verbatim_titles_and_intents_are_rejected(self):
        self.assertTrue(is_prompt_exemplar_copy({"title": PROMPT_EXEMPLAR_E2E_TITLE}))
        self.assertTrue(is_prompt_exemplar_copy({"title": PROMPT_EXEMPLAR_EDGE_TITLE}))
        self.assertTrue(is_prompt_exemplar_copy({"intent": PROMPT_EXEMPLAR_E2E_INTENT}))
        self.assertTrue(is_prompt_exemplar_copy({
            "preconditions": list(PROMPT_EXEMPLAR_E2E_PRECONDITIONS),
        }))

    def test_hybrid_scaffolding_is_rejected_when_absent_from_corpus(self):
        self.assertTrue(is_prompt_exemplar_copy(
            {"title": HYBRID_E2E_TITLE},
            PASSWORD_RESET_TEXT,
        ))

    def test_grounded_password_reset_case_is_kept(self):
        case = {"title": GROUNDED_RESET_TITLE}
        self.assertFalse(is_prompt_exemplar_copy(case, PASSWORD_RESET_TEXT))
        self.assertTrue(_case_has_source_grounding(case, PASSWORD_RESET_TEXT))

    def test_filter_strips_exemplars_and_keeps_grounded(self):
        kept = filter_prompt_exemplar_copies(
            [
                {"title": PROMPT_EXEMPLAR_E2E_TITLE},
                {"title": PROMPT_EXEMPLAR_EDGE_TITLE},
                {"title": HYBRID_E2E_TITLE},
                {"title": GROUNDED_RESET_TITLE},
            ],
            PASSWORD_RESET_TEXT,
        )
        self.assertEqual([GROUNDED_RESET_TITLE], [case["title"] for case in kept])

    def test_prompt_builder_interpolates_the_shared_exemplar_strings(self):
        prompt = build_e2e_agent_prompt(
            {
                "featureName": "Password reset",
                "featureDescription": "Reset a password by email",
                "summaries": {"prd": "", "hld": ""},
                "businessContext": {},
                "flags": {},
            },
            [],
            [],
            {},
            0,
        )
        self.assertIn(PROMPT_EXEMPLAR_E2E_TITLE, prompt)
        self.assertIn(PROMPT_EXEMPLAR_EDGE_TITLE, prompt)


class PromptExemplarPipelineTests(unittest.TestCase):
    def _llm(self, **overrides):
        payload = {
            "e2e_tests": [
                {
                    "title": PROMPT_EXEMPLAR_E2E_TITLE,
                    "intent": PROMPT_EXEMPLAR_E2E_INTENT,
                    "preconditions": list(PROMPT_EXEMPLAR_E2E_PRECONDITIONS),
                    "steps": [{"content": "Join", "expectedResult": "Fails"}],
                },
                {
                    "title": HYBRID_E2E_TITLE,
                    "steps": [{"content": "Send reset link", "expectedResult": "Fails"}],
                },
                {
                    "title": GROUNDED_RESET_TITLE,
                    "steps": [{
                        "content": "Request a password reset",
                        "expectedResult": "A reset email is sent",
                    }],
                },
            ],
            "edge_cases": [
                {
                    "title": PROMPT_EXEMPLAR_EDGE_TITLE,
                    "steps": [{"content": "Delete and join", "expectedResult": "Conflict"}],
                },
            ],
            "business_tests": [{
                "title": GROUNDED_RESET_TITLE,
                "steps": [{
                    "content": "Request a password reset",
                    "expectedResult": "A reset email is sent",
                }],
            }],
        }
        payload.update(overrides)
        return ScenarioLLM(e2e_payload=payload)

    def test_exemplar_payload_is_stripped_and_grounded_case_is_kept(self):
        store, llm = _password_reset_store(), self._llm()
        _run(store, llm)
        titles = _titles(store)
        self.assertNotIn(PROMPT_EXEMPLAR_E2E_TITLE, titles)
        self.assertNotIn(PROMPT_EXEMPLAR_EDGE_TITLE, titles)
        self.assertNotIn(HYBRID_E2E_TITLE, titles)
        self.assertIn(GROUNDED_RESET_TITLE, titles)

    def test_edge_exemplar_reclassified_as_e2e_is_still_dropped(self):
        store, llm = _password_reset_store(), self._llm(e2e_tests=[
            {
                "title": PROMPT_EXEMPLAR_EDGE_TITLE,
                "steps": [{"content": "Join", "expectedResult": "Conflict"}],
            },
            {
                "title": GROUNDED_RESET_TITLE,
                "steps": [{
                    "content": "Request a password reset",
                    "expectedResult": "A reset email is sent",
                }],
            },
        ], edge_cases=[])
        _run(store, llm)
        titles = _titles(store)
        self.assertNotIn(PROMPT_EXEMPLAR_EDGE_TITLE, titles)
        self.assertIn(GROUNDED_RESET_TITLE, titles)

    def test_zero_grounding_e2e_without_exemplar_title_is_dropped(self):
        store = _password_reset_store()
        llm = ScenarioLLM(e2e_payload={
            "e2e_tests": [
                {
                    "title": "Warehouse robots must dock after the night cycle",
                    "steps": [{"content": "Dock", "expectedResult": "Docked"}],
                },
                {
                    "title": GROUNDED_RESET_TITLE,
                    "steps": [{
                        "content": "Request a password reset",
                        "expectedResult": "A reset email is sent",
                    }],
                },
            ],
            "edge_cases": [],
            "business_tests": [],
        })
        _run(store, llm)
        titles = _titles(store)
        self.assertNotIn("Warehouse robots must dock after the night cycle", titles)
        self.assertIn(GROUNDED_RESET_TITLE, titles)
