import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const src = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../src/compat/runtime/controllers/00-core.js"),
  "utf8",
);
const start = src.indexOf("const BOOT_VECTOR_SEARCH_MSG");
const end = src.indexOf("async function refreshStatus");
assert.ok(start > 0 && end > start, "boot status helpers should exist in 00-core.js");

const esc = (s) =>
  (s ?? "").toString().replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c],
  );

const { looksLikeRawBootDetail, formatBootStatus, BOOT_VECTOR_SEARCH_MSG, bootBannerDetailsHtml } =
  new Function(
    "esc",
    `${src.slice(start, end)}\nreturn { looksLikeRawBootDetail, formatBootStatus, BOOT_VECTOR_SEARCH_MSG, bootBannerDetailsHtml };`,
  )(esc);

const RAW_INDEX =
  "index retry: recv(): message msgLen 68288512 is invalid. Min 16 Max: 48000000, full error: {'ok': 0.0, 'errmsg': 'recv(): message msgLen 68288512 is invalid. Min 16 Max: 48000000', 'code': 17, 'codeName': 'ProtocolError', '$clusterTime': {'clusterTime': Timestamp(...)}}";

test("raw driver dumps are not treated as safe primary copy", () => {
  assert.equal(looksLikeRawBootDetail(RAW_INDEX), true);
  assert.equal(looksLikeRawBootDetail(BOOT_VECTOR_SEARCH_MSG), false);
  assert.equal(
    looksLikeRawBootDetail(
      "This MongoDB Atlas cluster doesn't allow enough search indexes. wardenIQ needs 6, but your tier caps them.",
    ),
    false,
  );
});

test("failed boot shows the Vector Search message and hides the dump", () => {
  const msg = formatBootStatus({ ready: false, stage: "error", detail: RAW_INDEX });
  assert.equal(msg.visible, true);
  assert.equal(msg.kind, "error");
  assert.equal(msg.summary, BOOT_VECTOR_SEARCH_MSG);
  assert.equal(msg.raw, RAW_INDEX);
  assert.equal(msg.summary.includes("msgLen"), false);
  assert.equal(msg.summary.includes("ProtocolError"), false);
});

test("human-readable error detail stays primary", () => {
  const msg = formatBootStatus({
    ready: false,
    stage: "error",
    detail: BOOT_VECTOR_SEARCH_MSG,
  });
  assert.equal(msg.summary, BOOT_VECTOR_SEARCH_MSG);
  assert.equal(msg.raw, "");
});

test("indexing retries use a short stage line and keep the dump in details", () => {
  const msg = formatBootStatus({ ready: false, stage: "indexing", detail: RAW_INDEX });
  assert.equal(msg.visible, true);
  assert.equal(msg.kind, "warn");
  assert.equal(msg.summary, "Setting up Vector Search indexes…");
  assert.equal(msg.raw, RAW_INDEX);
});

test("ready boot hides the banner", () => {
  const msg = formatBootStatus({ ready: true, stage: "ready", detail: "" });
  assert.equal(msg.visible, false);
});

test("details markup is omitted unless there is raw text", () => {
  assert.equal(bootBannerDetailsHtml(""), "");
  assert.match(bootBannerDetailsHtml(RAW_INDEX), /<summary>Details<\/summary>/);
  assert.match(bootBannerDetailsHtml(RAW_INDEX), /ProtocolError/);
  assert.equal(bootBannerDetailsHtml(RAW_INDEX).includes("<script>"), false);
});
