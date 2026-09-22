import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import vm from "node:vm";

// The compatibility controller shares globals with the shell. Execute its login
// functions with a tiny DOM/API harness, without the unrelated event bindings.
const source = readFileSync(
  new URL("../src/compat/runtime/controllers/10-auth.js", import.meta.url), "utf8",
).split("function applyRole()")[0];

function harness(api) {
  const nodes = new Map();
  const timers = [];
  const $ = (selector) => {
    if (!nodes.has(selector)) nodes.set(selector, { hidden: true, textContent: "", focus() {} });
    return nodes.get(selector);
  };
  $("#login").hidden = false;
  const context = vm.createContext({
    $, api, ME: null, clearLoginCode() {},
    setTimeout(fn, delay) { timers.push({ fn, delay }); },
  });
  vm.runInContext(source, context);
  return { $, timers, context, refresh: () => context.refreshLoginBootStatus(0) };
}

test("shows safe boot failure and recovery guidance as text", async () => {
  const h = harness(async () => ({ ready: false, detail: "Vector Search unavailable",
    recovery: "Run scripts/reset-admin-password.sh <operator>" }));
  await h.refresh();
  assert.equal(h.$("#login-boot-status").hidden, false);
  assert.equal(h.$("#login-boot-status").textContent,
    "Vector Search unavailable Run scripts/reset-admin-password.sh <operator>");
  assert.equal(h.timers[0].delay, 3000);
});

test("healthy sign-in leaves the boot banner hidden and stops polling", async () => {
  const h = harness(async () => ({ ready: true, detail: "" }));
  await h.refresh();
  assert.equal(h.$("#login-boot-status").hidden, true);
  assert.equal(h.$("#login-boot-status").textContent, "");
  assert.equal(h.timers.length, 0);
});

test("a startup warning disappears once boot completes", async () => {
  let ready = false;
  const h = harness(async () => ({ ready, detail: "Connecting" }));
  await h.refresh();
  ready = true;
  await h.timers.shift().fn();
  assert.equal(h.$("#login-boot-status").hidden, true);
  assert.equal(h.timers.length, 0);
});

test("leaving the login screen stops polling", async () => {
  let calls = 0;
  const h = harness(async () => { calls++; return { ready: false, detail: "Starting" }; });
  await h.refresh();
  h.$("#login").hidden = true;
  await h.timers.shift().fn();
  assert.equal(calls, 1);
  assert.equal(h.timers.length, 0);
});

test("a transient request error preserves the diagnosis and retries", async () => {
  const h = harness(async () => { throw new Error("offline"); });
  h.$("#login-boot-status").textContent = "Useful diagnosis";
  await h.refresh();
  assert.equal(h.$("#login-boot-status").textContent, "Useful diagnosis");
  assert.equal(h.timers.length, 1);
});

test("an old login request cannot overwrite the current login state", async () => {
  let resolve;
  const h = harness(() => new Promise((done) => { resolve = done; }));
  const pending = h.refresh();
  vm.runInContext("loginBootPoll++", h.context);
  resolve({ ready: false, detail: "Stale" });
  await pending;
  assert.equal(h.$("#login-boot-status").textContent, "");
  assert.equal(h.timers.length, 0);
});

test("showLogin requests diagnostics even while SMTP status is pending", async () => {
  const calls = [];
  const h = harness(async (path) => {
    calls.push(path);
    if (path.endsWith("boot-status")) return { ready: false, detail: "Search unavailable" };
    return new Promise(() => {});
  });
  void h.context.showLogin();
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(calls, ["/api/auth/boot-status", "/api/auth/smtp-status"]);
  assert.equal(h.$("#login-boot-status").textContent, "Search unavailable");
});
