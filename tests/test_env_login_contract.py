"""The .env sign-in contract, as an operator reads it off the file.

    ADMIN_EMAIL / ADMIN_PASSWORD blank  ->  `admin` / admin123 signs in.
    ADMIN_PASSWORD set                  ->  that password signs in, for `admin`
                                            AND for ADMIN_EMAIL. admin123 is dead.

This is the rule the whole feature exists to satisfy, so it's pinned end-to-end:
the boot-time seed (`_seed_bootstrap_password`) and the sign-in route
(`login_password`) are exercised together, in that order, against one fake store —
the same sequence a container performs. Testing them separately would let the pair
drift apart while both files' own tests still pass.
"""
import importlib
import sys

import pytest

ADMIN_EMAIL = "jayesh@adlerqa.in"
ENV_PASSWORD = "HwVxS9COUAOVYqha"
SHIPPED_DEFAULT = "admin123"


class FakeStore:
    def __init__(self):
        self.users = {}
        self._n = 0

    def get_user_by_email(self, email):
        return self.users.get((email or "").strip().lower())

    def create_user(self, email, name, role="viewer", **kw):
        self._n += 1
        u = {"id": f"id-{self._n}", "email": email.strip().lower(), "name": name,
             "role": role, "active": True, "session_version": 0}
        self.users[u["email"]] = u
        return u

    def get_user(self, uid):
        return next((u for u in self.users.values() if u["id"] == uid), None)

    def set_user_password(self, uid, password_hash):
        u = self.get_user(uid)
        u["password_hash"] = password_hash
        u["session_version"] = u.get("session_version", 0) + 1
        return u

    def touch_login(self, uid):
        pass


class FakeResponse:
    def __init__(self):
        self.cookies = {}

    def set_cookie(self, name, value, **kwargs):
        self.cookies[name] = value


@pytest.fixture
def app_modules():
    sys.path.insert(0, "app")
    return (importlib.import_module("core.bootstrap"),
            importlib.import_module("api.routes.auth"),
            importlib.import_module("auth"))


def boot(app_modules, monkeypatch, admin_email="", admin_password=""):
    """Simulate a container boot with this .env, and return the store it produced.

    Mirrors bootstrap(): seed the ADMIN_EMAIL row, then seed the password. Also
    resolves DEFAULT_ADMIN_PASSWORD the way core/config.py does, so the route under
    test sees the value this .env would really give it.
    """
    bootstrap, routes, auth = app_modules
    store = FakeStore()
    monkeypatch.setattr(bootstrap, "store", store)
    monkeypatch.setattr(routes, "store", store)
    monkeypatch.setattr(bootstrap, "ADMIN_EMAIL", admin_email)
    monkeypatch.setattr(bootstrap, "ADMIN_PASSWORD", admin_password)
    monkeypatch.delenv("RESET_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_FORCE", raising=False)

    effective_default = (admin_password
                         if admin_password and not auth.password_policy_errors(admin_password)
                         else SHIPPED_DEFAULT)
    monkeypatch.setattr(routes, "DEFAULT_ADMIN_PASSWORD", effective_default)
    monkeypatch.setattr(routes, "_smtp_cfg", lambda: None)

    # bootstrap(): ADMIN_EMAIL seed, then the password seed.
    if admin_email and auth.is_valid_email(admin_email):
        store.create_user(admin_email, admin_email.split("@")[0], "admin")
    bootstrap._seed_bootstrap_password()
    return store


def signs_in(app_modules, username, password):
    _, routes, _ = app_modules
    body = routes.LoginPasswordIn(username=username, password=password)
    try:
        routes.login_password(body, FakeResponse())
        return True
    except routes.HTTPException:
        return False


# ------------------------------------------- nothing in .env -> admin / admin123
def test_empty_env_admin123_signs_in(app_modules, monkeypatch):
    boot(app_modules, monkeypatch)
    assert signs_in(app_modules, "admin", SHIPPED_DEFAULT)


def test_empty_env_seeds_nothing(app_modules, monkeypatch):
    """No ADMIN_PASSWORD means no row is created or written at boot."""
    store = boot(app_modules, monkeypatch)
    assert store.users == {}


def test_empty_env_rejects_other_passwords(app_modules, monkeypatch):
    boot(app_modules, monkeypatch)
    for pw in ("", "wrong", ENV_PASSWORD):
        assert not signs_in(app_modules, "admin", pw)


# ------------------------------- password in .env -> that password, both usernames
def test_env_password_signs_in_as_admin(app_modules, monkeypatch):
    boot(app_modules, monkeypatch, ADMIN_EMAIL, ENV_PASSWORD)
    assert signs_in(app_modules, "admin", ENV_PASSWORD)


def test_env_password_signs_in_as_the_configured_email(app_modules, monkeypatch):
    """The point of the whole change: the .env pair works as a pair."""
    boot(app_modules, monkeypatch, ADMIN_EMAIL, ENV_PASSWORD)
    assert signs_in(app_modules, ADMIN_EMAIL, ENV_PASSWORD)


def test_env_password_kills_admin123(app_modules, monkeypatch):
    boot(app_modules, monkeypatch, ADMIN_EMAIL, ENV_PASSWORD)
    assert not signs_in(app_modules, "admin", SHIPPED_DEFAULT)
    assert not signs_in(app_modules, ADMIN_EMAIL, SHIPPED_DEFAULT)


def test_password_without_email_still_covers_admin(app_modules, monkeypatch):
    """ADMIN_PASSWORD alone: `admin` takes it, and no stray row appears."""
    store = boot(app_modules, monkeypatch, "", ENV_PASSWORD)
    assert signs_in(app_modules, "admin", ENV_PASSWORD)
    assert list(store.users) == ["admin"]


def test_email_without_password_leaves_admin123_in_place(app_modules, monkeypatch):
    """ADMIN_EMAIL alone: there is no password to sign in with, so the email is
    OTP-only and the shipped default still covers `admin`."""
    boot(app_modules, monkeypatch, ADMIN_EMAIL, "")
    assert signs_in(app_modules, "admin", SHIPPED_DEFAULT)
    assert not signs_in(app_modules, ADMIN_EMAIL, SHIPPED_DEFAULT)


# ----------------------------------------------------------------- edge handling
def test_policy_violating_env_password_falls_back_to_admin123(app_modules, monkeypatch):
    """A rejected ADMIN_PASSWORD must not half-apply: nothing seeded, default stands."""
    store = boot(app_modules, monkeypatch, ADMIN_EMAIL, "short")
    assert signs_in(app_modules, "admin", SHIPPED_DEFAULT)
    assert "password_hash" not in store.users[ADMIN_EMAIL]


def test_env_password_equal_to_the_shipped_default_is_rejected(app_modules, monkeypatch):
    """admin123 fails the policy, so setting it in .env changes nothing."""
    store = boot(app_modules, monkeypatch, ADMIN_EMAIL, SHIPPED_DEFAULT)
    assert "password_hash" not in store.users[ADMIN_EMAIL]
    assert signs_in(app_modules, "admin", SHIPPED_DEFAULT)


def test_in_app_password_change_survives_a_restart(app_modules, monkeypatch):
    """Reboot with the same .env must not reset a password changed in-app."""
    bootstrap, _, auth = app_modules
    store = boot(app_modules, monkeypatch, ADMIN_EMAIL, ENV_PASSWORD)
    chosen = "M7ChosenInApp"
    store.set_user_password(store.users[ADMIN_EMAIL]["id"], auth.hash_password(chosen))
    bootstrap._seed_bootstrap_password()  # second boot, same .env
    assert signs_in(app_modules, ADMIN_EMAIL, chosen)
    assert not signs_in(app_modules, ADMIN_EMAIL, ENV_PASSWORD)


def test_reset_admin_password_overrides_an_existing_password(app_modules, monkeypatch):
    """The documented escape hatch: unlike the seed, it DOES clobber."""
    bootstrap, _, auth = app_modules
    store = boot(app_modules, monkeypatch, ADMIN_EMAIL, ENV_PASSWORD)
    forced = "F0rcedReset99"
    monkeypatch.setenv("RESET_ADMIN_PASSWORD", forced)
    bootstrap._seed_bootstrap_password()
    for who in ("admin", ADMIN_EMAIL):
        assert auth.password_matches(store.users[who]["password_hash"], forced)


def test_env_example_has_no_inline_comments():
    """Ensure no variable lines in .env.example contain inline '#' comments.

    Trailing comments on value lines leak into parsed environment variables
    under Docker Compose env_file, shell source, or certain dotenv parsers.
    Comments must live on their own lines above the variable.
    """
    import re
    from pathlib import Path

    env_path = Path(__file__).resolve().parent.parent / ".env.example"
    assert env_path.exists(), ".env.example should exist at repo root"

    inline_comment_pattern = re.compile(r"^[A-Z_]+=.*#")
    violations = []

    for lineno, line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        if inline_comment_pattern.match(line):
            violations.append(f"Line {lineno}: {line}")

    assert not violations, (
        f"Found inline comments in .env.example:\n" + "\n".join(violations) +
        "\nMove comments onto their own line above the variable."
    )

