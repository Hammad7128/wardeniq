"""Ticket: "when trying to create a new cycle without giving cycle name should
not be allowed, currently it creates new name with Cycle (date)".

Repro (Test Cycles page): leave "Cycle name" blank, click "+ New cycle". The
frontend's `createEmptyCycle()` (08-code-analysis-and-cycles.js) silently
substituted `Cycle ${new Date().toLocaleDateString()}` for the blank field
instead of requiring a name. A second blank-name click on the same day then
collided on that exact same auto-generated name and surfaced a confusing
"A test cycle with this name already exists in this project" toast -- the
user never gets told the real problem, which is that no name was given at all.
The identical "|| Cycle ${date}" fallback was duplicated in
`createCycleFromSelection()` (the Code Analysis "create cycle from impacted
cases" flow) and, via `create_cycle_from_template()` delegating straight into
`Store.create_cycle()`, was never guarded against on the backend at all --
any direct API caller (or a future frontend flow) could create a nameless
cycle with no pushback whatsoever.

Fix: `Store.create_cycle()` -- the single method all three creation paths
funnel through -- now rejects a blank/whitespace-only name with a plain
ValueError("Cycle name is required"), the same way it already rejects a
colliding name. The route (app/api/routes/test_cycles.py) already turns any
ValueError from this method into an HTTP 409 with the message, so this needed
no route change.

Uses mongomock (real MongoDB-aggregation/find semantics) so `create_cycle()`'s
actual find-then-insert flow is genuinely exercised, not just asserted.
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


class TestCycleNameRequired:
    def test_blank_name_is_rejected(self, mongo_store):
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle("p1", "", [])

    def test_whitespace_only_name_is_rejected(self, mongo_store):
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle("p1", "   ", [])

    def test_none_name_is_rejected(self, mongo_store):
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle("p1", None, [])

    def test_rejected_creation_leaves_no_cycle_behind(self, mongo_store):
        with pytest.raises(ValueError):
            mongo_store.create_cycle("p1", "", [])
        assert mongo_store.list_cycles("p1") == []

    def test_a_second_blank_attempt_still_says_name_required_not_duplicate(self, mongo_store):
        """The exact ticket symptom: two blank-name submissions used to collide
        on the identical auto-generated fallback name and surface a confusing
        "already exists" error. Both attempts must now fail for the real
        reason -- no name -- not a duplicate-name conflict."""
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle("p1", "", [])
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle("p1", "", [])

    def test_real_name_still_works_and_is_trimmed(self, mongo_store):
        cid = mongo_store.create_cycle("p1", "  Sprint 12 regression  ", [])
        cycles = mongo_store.list_cycles("p1")
        assert len(cycles) == 1
        assert cycles[0]["name"] == "Sprint 12 regression"

    def test_duplicate_real_name_is_still_rejected_as_before(self, mongo_store):
        mongo_store.create_cycle("p1", "Sprint 12 regression", [])
        with pytest.raises(ValueError, match="already exists"):
            mongo_store.create_cycle("p1", "Sprint 12 regression", [])

    def test_create_from_template_also_rejects_a_blank_name(self, mongo_store):
        """create_cycle_from_template() delegates straight into create_cycle()
        -- confirms the guard protects that entry point too, with no separate
        fix needed there."""
        cid = mongo_store.create_cycle("p1", "Base cycle", [])
        tid = mongo_store.save_cycle_as_template(cid, "My template")
        with pytest.raises(ValueError, match="[Nn]ame is required"):
            mongo_store.create_cycle_from_template(tid, "   ")
