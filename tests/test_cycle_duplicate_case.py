"""Ticket: "Duplicate test case can be created for the same feature within the
same test cycle" -- using "Add Test Cases" -> "Create a new test case" inside an
open cycle, entering the exact same title/steps/expected-results as an existing
test case already in that cycle for the same feature succeeds with no
duplicate-validation warning.

Root cause: `create_test_case()` (app/api/routes/steps_test_cases.py) has no
notion of "cycle" at all -- its `NewCaseIn` schema has no `cycle_id` field -- so
it always creates a brand-new case document with a brand-new case_id. The
frontend then makes a SEPARATE call to `add_cycle_items()`
(app/store/test_cycles.py) to link that new case into the cycle. That function's
only duplicate guard was `case_id in existing` -- which can never fire for a
freshly created duplicate, since by construction it has a different case_id from
the case it duplicates. No other layer (frontend or backend) checked
title/feature equality against the cycle's own existing items.

Fix: `add_cycle_items()` now also checks each incoming case's (feature_id, title)
against the (feature_id, title) pairs already denormalized onto the cycle's own
`items` (via `_cycle_item_from_case()`), case-insensitively and trimmed --
mirroring the same-style uniqueness check `create_cycle()` already does for
cycle names. On a match it raises ValueError, which the route
(app/api/routes/test_cycles.py) now catches and turns into a 400 with a clear
message, instead of the addition silently succeeding.

Uses mongomock (a real MongoDB-aggregation-semantics-compatible in-memory
server) so `Store.add_cycle_items()`/`create_cycle()`/`get_cycle()` are
genuinely exercised end to end against a real find/insert/update pipeline --
not just asserted to "look right" against a hand-mocked collection.
"""
from pathlib import Path
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


def _make_case(mongo_store, title, feature_id, type_="functional", priority="P2"):
    cid = mongo_store.cases.insert_one({
        "title": title, "type": type_, "priority": priority,
        "preconditions": "", "step_ids": [], "tags": [],
        "embedding": [0.1] * 8, "source_feature_id": feature_id,
        "status": "active",
    }).inserted_id
    return str(cid)


class TestCycleDuplicateCaseDetection:
    def test_new_case_with_same_title_and_feature_already_in_cycle_is_rejected(self, mongo_store):
        fid = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Checkout"}).inserted_id)
        original = _make_case(mongo_store, "Verify coupon code applies discount", fid)
        cycle_id = mongo_store.create_cycle("p1", "Sprint 12 regression", [original])

        # Simulates "Add Test Cases" -> "Create a new test case": the case is
        # created FIRST (its own, different, case_id), then the frontend tries to
        # link it into the cycle as a second call -- exactly like
        # 04-test-cases.js's saveCase() does.
        duplicate = _make_case(mongo_store, "Verify coupon code applies discount", fid)

        with pytest.raises(ValueError, match="already exists in this cycle"):
            mongo_store.add_cycle_items(cycle_id, [duplicate])

        # And the duplicate must not have been silently linked in anyway.
        cycle = mongo_store.get_cycle(cycle_id)
        case_ids_in_cycle = {item["case_id"] for item in cycle["items"]}
        assert case_ids_in_cycle == {original}

    def test_title_match_is_case_insensitive_and_trims_whitespace(self, mongo_store):
        fid = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Checkout"}).inserted_id)
        original = _make_case(mongo_store, "  Verify Coupon Code Applies Discount  ", fid)
        cycle_id = mongo_store.create_cycle("p1", "Sprint 12 regression", [original])
        duplicate = _make_case(mongo_store, "verify coupon code applies discount", fid)

        with pytest.raises(ValueError):
            mongo_store.add_cycle_items(cycle_id, [duplicate])

    def test_same_title_in_a_different_feature_is_allowed(self, mongo_store):
        f1 = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Checkout"}).inserted_id)
        f2 = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Login"}).inserted_id)
        case_f1 = _make_case(mongo_store, "Verify happy path", f1)
        cycle_id = mongo_store.create_cycle("p1", "Sprint 12 regression", [case_f1])
        case_f2 = _make_case(mongo_store, "Verify happy path", f2)

        added = mongo_store.add_cycle_items(cycle_id, [case_f2])
        assert added == 1
        cycle = mongo_store.get_cycle(cycle_id)
        case_ids_in_cycle = {item["case_id"] for item in cycle["items"]}
        assert case_ids_in_cycle == {case_f1, case_f2}

    def test_distinct_titles_in_the_same_feature_both_get_added(self, mongo_store):
        fid = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Checkout"}).inserted_id)
        c1 = _make_case(mongo_store, "Verify coupon code applies discount", fid)
        cycle_id = mongo_store.create_cycle("p1", "Sprint 12 regression", [c1])
        c2 = _make_case(mongo_store, "Verify expired coupon is rejected", fid)

        added = mongo_store.add_cycle_items(cycle_id, [c2])
        assert added == 1

    def test_re_adding_the_exact_same_case_id_is_still_a_silent_noop(self, mongo_store):
        """Pre-existing behavior (picking the same existing case twice in the
        "add existing cases" flow) must keep working exactly as before -- this
        fix must not turn that harmless idempotent re-add into an error."""
        fid = str(mongo_store.features.insert_one(
            {"project_id": "p1", "name": "Checkout"}).inserted_id)
        c1 = _make_case(mongo_store, "Verify coupon code applies discount", fid)
        cycle_id = mongo_store.create_cycle("p1", "Sprint 12 regression", [c1])

        added = mongo_store.add_cycle_items(cycle_id, [c1])
        assert added == 0
