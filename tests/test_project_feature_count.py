"""Ticket: "on creating new versions feature count is also increasing".

Repro (Projects page card, e.g. "Near-U — 4 features · 3 repositories"):
re-analyze/re-import an EXISTING feature to create a new version of it (not a
brand-new feature) -- the project's feature count on the card goes up by one,
exactly as if a new feature had been added.

Root cause: each version of a feature is its own document in the `features`
collection (`create_feature()`, app/store/features.py) -- all versions of the
same logical feature share one `group_id`, while each version gets its own
`_id`. The "create a new version" flow (app/api/routes/features.py's non-replace
branch of the "re-analyze" endpoint) calls
`store.create_feature(..., group_id=prev_group, version=new_v)`, which inserts
a brand-new document. `Store.list_projects()`'s `feature_count` was a raw
`self.features.count_documents({"project_id": pid})` over that collection --
counting every version document as its own feature, so a new version inflated
the count exactly like a new feature would. The Features page itself
(`list_features()`) already dedups by `group_id` and only shows the latest
version per group; the project card's count just never matched that.

Fix: `feature_count` is now computed by deduping `group_id` values (falling
back to the doc's own `_id` for legacy pre-versioning docs, same as
`list_features()` does), so adding a version to an existing feature no longer
changes the count, while adding a genuinely new feature still does.

Uses mongomock (real find/count semantics) so `list_projects()`'s actual query
is genuinely exercised end to end.
"""
from pathlib import Path
import sys

import pytest
from bson import ObjectId

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


def _feature_count(mongo_store, pid):
    projects = {p["id"]: p for p in mongo_store.list_projects()}
    return projects[pid]["feature_count"]


class TestProjectFeatureCount:
    def test_creating_a_new_version_of_an_existing_feature_does_not_increase_count(self, mongo_store):
        pid = mongo_store.create_project("Near-U")
        f1 = mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "some text v1", "summary v1", [0.1] * 8)
        assert _feature_count(mongo_store, pid) == 1

        # Simulate the real "create a new version" flow exactly the way
        # app/api/routes/features.py's re-analyze (non-replace) branch does:
        # same group_id as the existing feature, version bumped.
        f1_doc = mongo_store.features.find_one({"_id": ObjectId(f1)})
        group_id = f1_doc.get("group_id", f1)
        mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "some text v2", "summary v2", [0.2] * 8,
            group_id=group_id, version=2)

        # Still just ONE logical feature -- this is the exact ticket symptom.
        assert _feature_count(mongo_store, pid) == 1
        # And a third version shouldn't budge it either.
        mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "some text v3", "summary v3", [0.3] * 8,
            group_id=group_id, version=3)
        assert _feature_count(mongo_store, pid) == 1

    def test_a_genuinely_new_feature_still_increases_the_count(self, mongo_store):
        pid = mongo_store.create_project("Near-U")
        mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "text", "summary", [0.1] * 8)
        assert _feature_count(mongo_store, pid) == 1
        mongo_store.create_feature(
            "Checkout", pid, ["spec2.pdf"], "text2", "summary2", [0.2] * 8)
        assert _feature_count(mongo_store, pid) == 2

    def test_count_matches_what_the_features_page_actually_lists(self, mongo_store):
        pid = mongo_store.create_project("Near-U")
        f1 = mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "v1", "summary v1", [0.1] * 8)
        f1_doc = mongo_store.features.find_one({"_id": ObjectId(f1)})
        group_id = f1_doc.get("group_id", f1)
        mongo_store.create_feature(
            "Login", pid, ["spec.pdf"], "v2", "summary v2", [0.2] * 8,
            group_id=group_id, version=2)
        mongo_store.create_feature(
            "Checkout", pid, ["spec2.pdf"], "text2", "summary2", [0.3] * 8)

        assert _feature_count(mongo_store, pid) == len(mongo_store.list_features(pid))

    def test_pre_versioning_legacy_feature_without_group_id_counts_as_one(self, mongo_store):
        """Docs created before versioning existed have no group_id at all --
        list_features() falls back to the doc's own _id in that case, and the
        count must use the same fallback so the two stay consistent."""
        pid = mongo_store.create_project("Legacy Co")
        mongo_store.features.insert_one({
            "name": "Old feature", "project_id": pid, "sources": ["x"],
            "source": "x", "text": "t", "summary": "s", "embedding": [0.1] * 8,
            "created_at": 0,
            # deliberately no group_id / version, matching a pre-versioning doc
        })
        assert _feature_count(mongo_store, pid) == 1
