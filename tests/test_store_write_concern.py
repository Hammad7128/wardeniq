"""Regression coverage for the settings-durability fix.

Two QA reports turned out to share one root cause: a saved Jira integration
("Jira Configuration Is Not Persisted After Browser Restart") and a saved LLM
config ("LLM Status Incorrectly Shows Disconnected Until Configuration Is
Re-saved") both live in the same `settings` Mongo document, written through
`store.save_settings()` -> `BaseStore.client`. That client used pymongo's
un-annotated default write concern (`w=1`, acknowledged by the primary only),
so a routine primary election shortly after a save could roll the write back
before it replicated -- even though the save had already returned success.
`jira_client().ok()` and `LLM.health()` for a hosted provider are both pure
config-state checks (`bool(base_url and email and token)` / `bool(api_key and
model)`), so a rolled-back field shows up exactly as "not configured" /
"disconnected" until the same fields are saved again.

These tests pin `store.base._with_durable_write_concern` (no live MongoDB
needed -- pymongo's MongoClient parses connection options lazily) so a future
change can't silently drop the majority write concern for either bug class.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from pymongo import MongoClient  # noqa: E402

from store.base import _with_durable_write_concern  # noqa: E402


def test_bundled_default_uri_gets_majority_write_concern():
    uri = ("mongodb://mongod1.warden-net:27017,mongod2.warden-net:27017,"
           "mongod3.warden-net:27017/?replicaSet=rs0")
    fixed = _with_durable_write_concern(uri)
    assert "w=majority" in fixed
    assert "retryWrites=true" in fixed
    # Prove pymongo actually parses this into the intended write concern --
    # not just a cosmetic string change.
    client = MongoClient(fixed, connect=False)
    try:
        assert client.write_concern.document == {"w": "majority"}
        assert client.options.retry_writes is True
    finally:
        client.close()


def test_operators_explicit_write_concern_is_never_overridden():
    uri = "mongodb://u:p@h1:27017,h2:27017/mydb?replicaSet=rs0&authSource=admin&w=1"
    fixed = _with_durable_write_concern(uri)
    # retryWrites is filled in (it was missing), but the operator's own w=1
    # choice is left alone -- e.g. a single-node dev Mongo where majority
    # would just reduce to 1 anyway, but the choice is theirs to make.
    assert "w=1" in fixed
    assert "w=majority" not in fixed
    assert "retryWrites=true" in fixed
    client = MongoClient(fixed, connect=False)
    try:
        assert client.write_concern.document == {"w": 1}
    finally:
        client.close()


def test_uri_already_fully_specified_is_left_byte_for_byte_unchanged():
    uri = "mongodb://u:p@cluster-shard-00-00.example.net:27017/?replicaSet=rs0&retryWrites=true&w=majority"
    assert _with_durable_write_concern(uri) == uri


def test_non_string_input_falls_back_without_raising():
    # Best-effort: a value urlsplit can't handle at all (e.g. None, if some
    # caller ever passed a misconfigured env var through) must never crash
    # startup over connection-string cosmetics -- the except branch returns
    # the input unchanged.
    assert _with_durable_write_concern(None) is None
