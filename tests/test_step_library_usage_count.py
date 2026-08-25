"""Ticket: "Step usage count does not match the actual number of test cases" --
Step Library lists a step as used by 4 cases; opening its detail panel's "Used in
Cases" (a real `find()` over test cases, which the frontend calls via GET
/api/test-cases?step_id=...) shows only 3.

Root cause: `Store.list_steps()` (app/store/steps_test_cases.py) computed each
step's case-usage count via `$unwind` + `$group`/`$sum` over `cases.step_ids`.
`$sum` after `$unwind` counts one hit per ARRAY OCCURRENCE, not per case -- so a
single test case that legitimately references the same shared step twice in its
own script (e.g. "click the X button" used at step 2 and step 5) contributes 2 to
that count, not 1. `find({"step_ids": step_id})` (what the detail panel uses)
naturally returns each matching case document exactly once regardless of how many
times the id appears in its array, so the two numbers drift apart specifically
when this repeated-step-within-one-case pattern occurs.

Uses mongomock (a real MongoDB-aggregation-semantics-compatible in-memory server)
rather than mocking `Store.cases.aggregate` by hand, so the aggregation pipeline
itself is genuinely exercised end to end -- not just asserted to "look right".
"""
from pathlib import Path
import os
import sys

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "app"
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

mongomock = pytest.importorskip("mongomock")

import store.base as store_base  # noqa: E402
from store import Store  # noqa: E402


@pytest.fixture
def mongo_store(monkeypatch):
    monkeypatch.setattr(store_base, "MongoClient", mongomock.MongoClient)
    return Store("mongodb://localhost/?", "wardeniq_test", 8)


class TestStepLibraryUsageCount:
    def test_case_reusing_the_same_step_twice_is_not_double_counted(self, mongo_store):
        s1 = str(mongo_store.steps.insert_one(
            {"action": "Click the Join Event button", "expected": "Event joined",
             "embedding": [0.1] * 8, "usage_count": 3}).inserted_id)
        s2 = str(mongo_store.steps.insert_one(
            {"action": "Some other step", "expected": "Something else",
             "embedding": [0.2] * 8, "usage_count": 1}).inserted_id)

        # 3 DISTINCT cases use s1. Case C uses it TWICE in its own step_ids
        # (the exact real-world pattern the ticket's "4 vs 3" discrepancy
        # comes from) -- reproducing the QA-observed 4-cases-shown-but-3-real.
        mongo_store.cases.insert_one({"title": "Case A", "step_ids": [s1, s2]})
        mongo_store.cases.insert_one({"title": "Case B", "step_ids": [s1]})
        mongo_store.cases.insert_one({"title": "Case C", "step_ids": [s1, s2, s1]})

        listed = mongo_store.list_steps()
        by_id = {s["id"]: s for s in listed}

        # This must equal 3 (distinct cases), not 4 (raw step_ids occurrences).
        assert by_id[s1]["used_in_cases"] == 3
        # Sanity: s2 is referenced once each by A and C = 2 distinct cases, no
        # repeats within a single case, so this one was never affected by the bug.
        assert by_id[s2]["used_in_cases"] == 2

        # And this must match what the "Used in Cases" detail panel actually
        # shows -- a plain find() over cases referencing the step, which by
        # construction returns each matching case exactly once.
        real_case_count = mongo_store.cases.count_documents({"step_ids": s1})
        assert by_id[s1]["used_in_cases"] == real_case_count

    def test_step_used_only_once_reports_one(self, mongo_store):
        s1 = str(mongo_store.steps.insert_one(
            {"action": "A", "expected": "B", "embedding": [0.1] * 8}).inserted_id)
        mongo_store.cases.insert_one({"title": "Only case", "step_ids": [s1]})
        listed = mongo_store.list_steps()
        assert listed[0]["used_in_cases"] == 1

    def test_unused_step_reports_zero(self, mongo_store):
        mongo_store.steps.insert_one(
            {"action": "Unused", "expected": "N/A", "embedding": [0.1] * 8})
        listed = mongo_store.list_steps()
        assert listed[0]["used_in_cases"] == 0
