"""Integration coverage for the embedding-model-switch flow:

    POST /api/embedding/switch (app/api/routes/jobs_usage.py::switch_embedding)
      -> launches a "reembed" job
      -> workers/generation.py::_reembed_worker()
      -> app/store/base.py::Store.reembed_all()

Added for the RAG live-eval follow-up (validation report item 7 / fix item 3): a prior
read-only pass found this flow's PIECES individually tested (per-provider Embedder
request shaping, probe_dim()) but no test exercising the actual switch-and-migrate job
end-to-end. This file closes that gap.

Both tests below run against REAL production code -- Embedder.probe_dim()/embed(),
Store.reembed_all(), the actual switch_embedding()/_reembed_worker() functions -- and
a real mongomock-backed Store, so "the actual dimension is probed" and "stored vectors
are regenerated" are proven against genuine behavior, not a hand-rolled stand-in.

Exactly two things are stubbed, both deliberately external to what this flow itself
does, per the task instruction to mock external providers rather than hit them:
  - the embedding provider's network call (httpx.post) -- same technique
    tests/test_embeddings.py already uses. No real provider is ever contacted.
  - Store.drop_vector_indexes/create_vector_indexes, which call Atlas Search's
    create_search_index/list_search_indexes: an Atlas-only API mongomock cannot
    emulate, and (separately) create_vector_indexes retries for up to 24*5s per
    collection against a missing create_search_index if left unstubbed -- unrelated
    to whether vectors themselves get regenerated, which is what reembed_all (left
    real, unstubbed) is actually responsible for.

No real MongoDB or embedding provider is touched, and nothing here performs a real
model switch against any live/dev environment.
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

import embeddings  # noqa: E402
from api.routes import jobs_usage  # noqa: E402
from api.routes.jobs_usage import EmbeddingIn  # noqa: E402
from core import state  # noqa: E402
from workers import generation  # noqa: E402


class FakeResp:
    """Stands in for httpx's Response -- same shape as tests/test_embeddings.py's."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _saved_settings(store):
    """Read the settings document directly off the mongomock collection.

    tests/conftest.py permanently stubs `Store.get_settings = lambda self: {}` at
    class-definition time (so OTHER test files' Store instances don't try to dial a
    real MongoDB at import), and that stub is never undone for the rest of this
    pytest process -- it applies to every Store instance, including this file's
    mongomock-backed one. So verifying what switch_embedding() actually persisted
    means reading the raw document `save_settings()` wrote, not calling the
    (globally stubbed) `get_settings()` method."""
    return store.db["settings"].find_one({"_id": "app"}) or {}


def _patch_provider(monkeypatch, dim):
    """Stub ONLY the network call. Embedder.probe_dim()/embed() run for real and
    parse this response through the real per-provider parsing code."""
    def fake_post(url, **kw):
        return FakeResp({"data": [{"embedding": [0.1] * dim}], "usage": {}})
    monkeypatch.setattr(embeddings.httpx, "post", fake_post)


@pytest.fixture
def mongo_store(monkeypatch):
    monkeypatch.setattr(store_base, "MongoClient", mongomock.MongoClient)
    s = Store("mongodb://localhost/?", "wardeniq_test", 768)
    # See module docstring: Atlas Search index management isn't something mongomock
    # can emulate (and left real, create_vector_indexes' retry loop would hang for
    # minutes against a missing create_search_index) -- record calls instead.
    index_calls = []
    monkeypatch.setattr(s, "drop_vector_indexes", lambda: index_calls.append(("drop",)))
    monkeypatch.setattr(s, "create_vector_indexes", lambda dim: index_calls.append(("create", dim)))
    s._index_calls = index_calls
    return s


def _seed_documents(store):
    """One row per collection reembed_all() touches, all starting at the OLD
    dimension (768) with a zeroed embedding, so 'stored vectors are regenerated at
    the new dimension' has something real to assert against."""
    store.features.insert_one({"text": "Feature: OAuth login", "embedding": [0.0] * 768})
    store.fchunks.insert_one({"text": "POST /oauth/callback", "embedding": [0.0] * 768})
    step_id = store.steps.insert_one(
        {"action": "Click login", "expected": "Redirected to Google", "embedding": [0.0] * 768}
    ).inserted_id
    store.cases.insert_one(
        {"title": "OAuth happy path", "step_ids": [str(step_id)], "embedding": [0.0] * 768}
    )


# --------------------------------------------------------------------------------
# 1. switch_embedding(): probes the TRUE dimension, persists settings, launches job
# --------------------------------------------------------------------------------

class TestSwitchEmbeddingProbesRealDimension:
    def test_switch_embedding_probes_true_dimension_and_persists_settings(
        self, mongo_store, monkeypatch
    ):
        monkeypatch.setattr(jobs_usage, "store", mongo_store)
        _patch_provider(monkeypatch, dim=1024)
        # This test's scope is switch_embedding()'s own probe+persist logic, not the
        # real threaded reembed job (that's TestReembedWorkerRegeneratesVectors...
        # below, called synchronously) -- without this stub, the REAL launch_job
        # spins a background thread that runs _reembed_worker() against the
        # process's real core.state.store singleton (an unreachable placeholder
        # Mongo URI in this test env), which can hang/retry for a long time.
        monkeypatch.setattr(jobs_usage, "launch_job", lambda *a, **kw: "job-stub")

        result = jobs_usage.switch_embedding(
            EmbeddingIn(provider="voyage", model="voyage-3", api_key="k")
        )

        assert result["dim"] == 1024
        saved = _saved_settings(mongo_store)
        assert saved["embed_provider"] == "voyage"
        assert saved["embed_model"] == "voyage-3"
        assert saved["embed_dim"] == 1024

    def test_switch_embedding_measures_actual_dimension_not_a_hardcoded_guess(
        self, mongo_store, monkeypatch
    ):
        # EMBED_MODEL_OPTIONS (app/api/routes/settings.py) hints voyage-3 as 1024-d,
        # but that's documented as just a UI hint -- probe_dim() is supposed to be
        # authoritative. Have the fake provider return something else entirely and
        # confirm THAT is what gets measured and persisted, not the table value.
        monkeypatch.setattr(jobs_usage, "store", mongo_store)
        _patch_provider(monkeypatch, dim=777)
        monkeypatch.setattr(jobs_usage, "launch_job", lambda *a, **kw: "job-stub")  # see above

        result = jobs_usage.switch_embedding(
            EmbeddingIn(provider="voyage", model="voyage-3", api_key="k")
        )
        assert result["dim"] == 777
        assert _saved_settings(mongo_store)["embed_dim"] == 777

    def test_switch_embedding_launches_reembed_job_with_measured_dim(
        self, mongo_store, monkeypatch
    ):
        monkeypatch.setattr(jobs_usage, "store", mongo_store)
        _patch_provider(monkeypatch, dim=1536)
        launched = {}
        monkeypatch.setattr(
            jobs_usage, "launch_job",
            lambda jtype, params, label="": launched.update(jtype=jtype, params=params) or "job-1",
        )

        result = jobs_usage.switch_embedding(
            EmbeddingIn(provider="openai", model="text-embedding-3-small", api_key="k")
        )

        assert result["job_id"] == "job-1"
        assert launched["jtype"] == "reembed"
        assert launched["params"] == {"dim": 1536}

    def test_switch_embedding_rejects_provider_that_returns_no_usable_vector(
        self, mongo_store, monkeypatch
    ):
        monkeypatch.setattr(jobs_usage, "store", mongo_store)
        _patch_provider(monkeypatch, dim=0)  # provider returned an empty vector
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            jobs_usage.switch_embedding(
                EmbeddingIn(provider="voyage", model="voyage-3", api_key="k")
            )
        # Nothing should have been persisted or launched on a bad probe.
        assert _saved_settings(mongo_store) == {}


# --------------------------------------------------------------------------------
# 2. _reembed_worker(): regenerates every stored vector, rebuilds indexes in order
# --------------------------------------------------------------------------------

class TestReembedWorkerRegeneratesVectorsAndRebuildsIndexes:
    def _run_worker(self, mongo_store, monkeypatch, dim=1024):
        _seed_documents(mongo_store)
        monkeypatch.setattr(generation, "store", mongo_store)
        new_embedder = embeddings.Embedder(provider="voyage", model="voyage-3", dim=dim)
        monkeypatch.setattr(generation, "current_embedder", lambda: new_embedder)
        _patch_provider(monkeypatch, dim=dim)

        jid = mongo_store.create_job("reembed", {"dim": dim})
        original_embedder = state.embedder
        try:
            generation._reembed_worker(jid, {"dim": dim})
        finally:
            # _reembed_worker rebinds state.embedder as a real production side
            # effect (the app's one live-reassignment of the embedder singleton) --
            # restore it so this test can't leak a fake embedder into any other
            # test that runs in the same process afterwards.
            state.embedder = original_embedder
        return jid

    def test_reembed_worker_regenerates_every_stored_vector_at_new_dimension(
        self, mongo_store, monkeypatch
    ):
        jid = self._run_worker(mongo_store, monkeypatch, dim=1024)

        for doc in mongo_store.features.find({}):
            assert len(doc["embedding"]) == 1024
            assert any(v != 0.0 for v in doc["embedding"])
        for doc in mongo_store.fchunks.find({}):
            assert len(doc["embedding"]) == 1024
        for doc in mongo_store.steps.find({}):
            assert len(doc["embedding"]) == 1024
        for doc in mongo_store.cases.find({}):
            assert len(doc["embedding"]) == 1024

        job = mongo_store.get_job(jid)
        assert job["result"]["dim"] == 1024
        assert job["result"]["provider"] == "voyage"
        assert job["result"]["model"] == "voyage-3"
        assert job["result"]["reembedded"] == {
            "features": 1, "feature_chunks": 1, "test_steps": 1, "test_cases": 1,
        }

    def test_reembed_worker_drops_then_rebuilds_indexes_in_order_at_new_dim(
        self, mongo_store, monkeypatch
    ):
        self._run_worker(mongo_store, monkeypatch, dim=1024)

        kinds = [call[0] for call in mongo_store._index_calls]
        assert kinds[0] == "drop", "old indexes must be dropped BEFORE re-embedding starts"
        assert kinds[-1] == "create", "new indexes must be rebuilt AFTER re-embedding finishes"
        assert ("create", 1024) in mongo_store._index_calls

    def test_reembed_worker_marks_job_done(self, mongo_store, monkeypatch):
        jid = self._run_worker(mongo_store, monkeypatch, dim=1024)
        job = mongo_store.get_job(jid)
        assert job["stage"] == "done"
        assert job["progress"] == 100
