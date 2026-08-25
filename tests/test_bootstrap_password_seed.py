"""The .env bootstrap pair (ADMIN_EMAIL + ADMIN_PASSWORD) is a usable sign-in.

`ADMIN_PASSWORD` used to be seeded onto the local `admin` row only, so the
`ADMIN_EMAIL` admin was created with no password and the configured email +
password pair did not actually work — the only way to give that account a
password was /api/auth/reset-password-master. `_bootstrap_password_targets()`
now returns both rows, so the pair an operator writes into .env is the pair they
can sign in with.

Covers the seeding targets and the invariants that must survive it: the
ADMIN_EMAIL row is never CREATED here, an existing password is never clobbered,
and a malformed/absent ADMIN_EMAIL is ignored.
"""
import importlib
import sys

import pytest


class FakeStore:
    def __init__(self, users=None):
        self.users = {}
        self._next = 0
        for email, extra in (users or {}).items():
            self._insert(email, extra)
        self.password_writes = []

    def _insert(self, email, extra=None):
        self._next += 1
        u = {"id": f"id-{self._next}", "email": email.strip().lower(),
             "name": email, "role": "admin", "active": True, "session_version": 0}
        u.update(extra or {})
        self.users[u["email"]] = u
        return u

    def get_user_by_email(self, email):
        return self.users.get((email or "").strip().lower())

    def create_user(self, email, name, role="viewer", **kw):
        return self._insert(email, {"name": name, "role": role})

    def get_user(self, uid):
        return next((u for u in self.users.values() if u["id"] == uid), None)

    def set_user_password(self, uid, password_hash):
        u = self.get_user(uid)
        u["password_hash"] = password_hash
        u["session_version"] = u.get("session_version", 0) + 1
        self.password_writes.append(u["email"])
        return u


@pytest.fixture
def bootstrap():
    sys.path.insert(0, "app")
    return importlib.import_module("core.bootstrap")


def _targets(bootstrap, monkeypatch, store, admin_email):
    monkeypatch.setattr(bootstrap, "store", store)
    monkeypatch.setattr(bootstrap, "ADMIN_EMAIL", admin_email)
    return [r["email"] for r in bootstrap._bootstrap_password_targets()]


# ------------------------------------------------------------- the new behavior
def test_configured_email_is_a_password_target(bootstrap, monkeypatch):
    store = FakeStore({"admin": {}, "jayesh@adlerqa.in": {}})
    assert _targets(bootstrap, monkeypatch, store, "jayesh@adlerqa.in") == [
        "admin", "jayesh@adlerqa.in"]


def test_configured_email_is_matched_case_insensitively(bootstrap, monkeypatch):
    store = FakeStore({"admin": {}, "jayesh@adlerqa.in": {}})
    assert _targets(bootstrap, monkeypatch, store, "  Jayesh@AdlerQA.in ") == [
        "admin", "jayesh@adlerqa.in"]


def test_local_admin_row_is_created_when_missing(bootstrap, monkeypatch):
    store = FakeStore()
    assert _targets(bootstrap, monkeypatch, store, "") == ["admin"]
    assert "admin" in store.users


# ------------------------------------------------------------------- invariants
def test_configured_email_row_is_never_created_here(bootstrap, monkeypatch):
    """Creating it belongs to the ADMIN_EMAIL seed step, which validates the
    address first. If that step skipped it, this must not resurrect it."""
    store = FakeStore({"admin": {}})
    assert _targets(bootstrap, monkeypatch, store, "jayesh@adlerqa.in") == ["admin"]
    assert "jayesh@adlerqa.in" not in store.users


def test_malformed_admin_email_is_ignored(bootstrap, monkeypatch):
    store = FakeStore({"admin": {}})
    for bad in ("", "   ", "not-an-email", "# first admin on startup", "admin"):
        assert _targets(bootstrap, monkeypatch, store, bad) == ["admin"]


def test_admin_is_not_listed_twice(bootstrap, monkeypatch):
    """ADMIN_EMAIL="admin" must not yield the same row as two targets."""
    store = FakeStore({"admin": {}})
    assert _targets(bootstrap, monkeypatch, store, "admin") == ["admin"]


def test_existing_password_is_not_clobbered(bootstrap, monkeypatch):
    """The seed path is `if not row.get("password_hash")` — an operator who changed
    their password in-app must keep it across restarts."""
    store = FakeStore({"admin": {"password_hash": "kept-hash"},
                       "jayesh@adlerqa.in": {"password_hash": "kept-too"}})
    targets = _targets(bootstrap, monkeypatch, store, "jayesh@adlerqa.in")
    assert targets == ["admin", "jayesh@adlerqa.in"]
    # Nothing was rewritten just by resolving targets.
    assert store.password_writes == []
    for row in store.users.values():
        assert row["password_hash"] in ("kept-hash", "kept-too")
