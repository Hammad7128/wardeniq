// ---- Import Sheet ----
// Track which feature the import modals operate on (set by entry-point handlers).
let IMP_FID = null,
  IMP_PID = null;
let IMP_FILE_NAME = "";
let IMPLIB_ITEMS = [];
let IMPLIB_DESIRED = new Map();

window.openImportSheetModal = async (fid, pid) => {
  IMP_FID = fid || currentFeature || null;
  IMP_PID = pid || currentProject || null;
  if (!IMP_FID || !IMP_PID) {
    toast("Open a feature first", true);
    return;
  }
  IMP_FILE_NAME = "";
  const fname =
    currentFeatureData && currentFeatureData.id === IMP_FID
      ? currentFeatureData.name
      : $("#d-name")?.textContent || "this feature";
  $("#imp-heading").textContent = "Import test cases";
  $("#imp-subtitle").innerHTML = `Updating: <b>${esc(fname)}</b>`;
  $("#imp-modal").classList.add("show");
  $("#imp-file").value = "";
  $("#imp-selected").textContent = "Selected: none";
  $("#imp-status").textContent = "";
  $("#imp-summary").innerHTML = "";
  $("#imp-upload").disabled = false;
  $("#imp-upload").style.display = "";
  $("#imp-cancel").textContent = "Cancel";
  $("#imp-progress").hidden = true;
};
window.importSheetForFeature = (fid, pid) => openImportSheetModal(fid, pid);
window.reuseImportsForFeature = (fid) => openImportLibraryModal(fid);

// Event-delegated handlers — the modals live OUTSIDE the original <script> tag,
// so direct $("#…").onclick assignments at script-parse time wouldn't bind.
document.addEventListener("click", (e) => {
  const actionEl = e.target.closest("[data-implib-action]");
  if (actionEl) {
    e.preventDefault();
    e.stopPropagation();
    handleImplibAction(actionEl);
    return;
  }
  const t = e.target.closest("button");
  if (!t || !t.id) return;
  if (t.id === "imp-close" || t.id === "imp-cancel") {
    $("#imp-modal").classList.remove("show");
  } else if (t.id === "imp-file-pick") {
    $("#imp-file").click();
  } else if (t.id === "imp-file-clear") {
    $("#imp-file").value = "";
    IMP_FILE_NAME = "";
    $("#imp-selected").textContent = "Selected: none";
    $("#imp-summary").innerHTML = "";
    $("#imp-status").textContent = "";
    $("#imp-upload").style.display = "";
    $("#imp-cancel").textContent = "Cancel";
    $("#imp-progress").hidden = true;
  } else if (t.id === "imp-template-xlsx" || t.id === "imp-template-csv") {
    const fmt = t.id === "imp-template-csv" ? "csv" : "xlsx";
    const fid = IMP_FID || currentFeature || "_";
    window.location.href = `/api/features/${fid}/tests/import/template?format=${fmt}`;
  } else if (t.id === "imp-upload") {
    runImpUpload();
  } else if (t.id === "implib-close") {
    $("#implib-modal").classList.remove("show");
  } else if (t.id === "implib-refresh") {
    runImplibRefresh();
  } else if (t.id === "implib-cancel") {
    $("#implib-modal").classList.remove("show");
  } else if (t.id === "implib-save") {
    saveImplibChanges();
  }
});

document.addEventListener("change", (e) => {
  if (e.target && e.target.id === "imp-file") {
    const f = e.target.files && e.target.files[0];
    IMP_FILE_NAME = f ? f.name : "";
    $("#imp-selected").textContent = `Selected: ${IMP_FILE_NAME || "none"}`;
    $("#imp-summary").innerHTML = "";
    $("#imp-status").textContent = "";
    $("#imp-upload").style.display = "";
    $("#imp-cancel").textContent = "Cancel";
    $("#imp-progress").hidden = true;
  }
});

// Also close modals when clicking outside the inner box.
document.addEventListener("click", (e) => {
  if (e.target && e.target.id === "imp-modal")
    $("#imp-modal").classList.remove("show");
  if (e.target && e.target.id === "implib-modal")
    $("#implib-modal").classList.remove("show");
});

async function runImpUpload() {
  const f = $("#imp-file").files && $("#imp-file").files[0];
  if (!f) {
    toast("Pick a file first", true);
    return;
  }
  const fid = IMP_FID || currentFeature;
  const pid = IMP_PID || currentProject;
  if (!fid || !pid) {
    toast("No feature in scope", true);
    return;
  }
  $("#imp-heading").textContent = "Import test cases";
  $("#imp-status").innerHTML = `<span>AI analyzing test cases...</span>`;
  $("#imp-summary").innerHTML = "";
  $("#imp-progress").hidden = false;
  $("#imp-upload").disabled = true;
  const fd = new FormData();
  fd.append("file", f);
  let resp;
  try {
    const r = await fetch(`/api/projects/${pid}/features/${fid}/tests/import`, {
      method: "POST",
      body: fd,
    });
    resp = await r.json();
    if (!r.ok) throw new Error(resp.detail || `${r.status}`);
    if (resp.alreadyUploaded) toast("Already uploaded · reusing saved import");
  } catch (e) {
    toast(e.message, true);
    $("#imp-upload").disabled = false;
    $("#imp-progress").hidden = true;
    $("#imp-status").innerHTML = `<span class="err">${esc(e.message)}</span>`;
    return;
  }
  const iid = resp.feature_import_id;
  const start = Date.now();
  async function pollImport() {
    let s;
    try {
      s = await api(`/api/features/${fid}/tests/import/${iid}/status`);
    } catch (e) {
      s = null;
    }
    if (!s) {
      $("#imp-upload").disabled = false;
      return;
    }
    const d = s.data || {};
    $("#imp-status").innerHTML =
      `<span>${esc(d.details || d.status || "AI analyzing test cases...")}</span>`;
    if (d.completed) {
      $("#imp-progress").hidden = true;
      renderImportSummary(d.result_json || {}, fid, iid);
      $("#imp-upload").disabled = false;
      return;
    }
    if (Date.now() - start > 5 * 60 * 1000) {
      $("#imp-upload").disabled = false;
      return;
    }
    setTimeout(pollImport, 1500);
  }
  pollImport();
}

// Post-import review state (GAP1): one entry per row with the reviewer's current
// include/exclude decision + note. Seeded from the scorer's action.
let IMP_REVIEW = [];
let IMP_REVIEW_CTX = { fid: null, iid: null };

function renderImportSummary(data, fid, iid) {
  const items = data.items || [];
  IMP_REVIEW_CTX = { fid, iid };
  IMP_REVIEW = items.map((it) => ({
    rid: it.project_imported_row_id || null,
    hash: it.identity_hash || null,
    included: it.action === "matched",
    note: "",
  }));
  if (!items.length) {
    $("#imp-heading").textContent = "Spreadsheet import finished";
    $("#imp-upload").style.display = "none";
    $("#imp-cancel").textContent = "Close";
    $("#imp-status").innerHTML = data.alreadyUploaded
      ? `<span class="ok">✓ Already uploaded · no parsing was repeated</span>`
      : `<span class="muted">No test rows recognized in this sheet.</span>`;
    return;
  }
  const matched = items.filter((i) => i.action === "matched").length;
  const stored = items.filter((i) => i.action !== "matched").length;
  const duplicateMerges = items.filter((i) => i.already_uploaded).length;
  const rejected = data.rejected_count || 0;
  $("#imp-heading").textContent = "Spreadsheet import finished";
  $("#imp-subtitle").innerHTML =
    `Imported into <b>${esc(currentFeatureData?.name || $("#d-name")?.textContent || "this feature")}</b>`;
  $("#imp-upload").style.display = "none";
  $("#imp-cancel").textContent = "Close";
  $("#imp-status").innerHTML = "";
  $("#imp-summary").innerHTML = `
    <div class="sheet-chip-row" style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 18px">
      <span class="pill">${esc(IMP_FILE_NAME || "Uploaded sheet")}</span>
      ${data.alreadyUploaded ? `<span class="sheet-pill green">Already uploaded</span>` : `<span class="sheet-pill green">First import for this feature</span>`}
    </div>
    ${sheetKpis([
      ["Included", matched, "green", "OK"],
      ["Stored for later", stored, "amber", "BOX"],
      ["Rejected", rejected, "red", "!"],
      ["Duplicate merges", duplicateMerges, "purple", "NET"],
    ])}
    <div class="sheet-meta-row">
      <b>Total rows: ${items.length}</b>
      <span>Processed rows: ${items.length}</span>
    </div>
    <div class="sheet-section-head">
      <div>
        <div class="typehdr">Review imported tests</div>
        <div class="muted">Include a row in this feature, or keep it in the project library for later. Then save.</div>
      </div>
      <button class="go" onclick="impSaveReview()" style="margin:0">Save review</button>
    </div>
    <div class="sheet-list" id="imp-review-list">${items.map((it, i) => renderImportDetailCard(it, i)).join("")}</div>
  `;
  if (matched > 0) {
    // Reload the feature list + workspace if open, so the new test cases appear.
    if (typeof loadFeatures === "function") loadFeatures();
    if (fid && currentFeature === fid && typeof openFeature === "function") {
      setTimeout(() => openFeature(currentFeature), 300);
    }
  }
}

function sheetKpis(defs) {
  return `<div class="sheet-summary-grid">${defs
    .map(
      ([label, value, color, icon]) => `
    <div class="sheet-kpi ${color}">
      <div class="l">${esc(label)}</div>
      <div class="v">${value}</div>
      <div class="ico">${esc(icon)}</div>
    </div>`,
    )
    .join("")}</div>`;
}

function renderImportDetailCard(it, idx) {
  const rv =
    typeof idx === "number" && IMP_REVIEW[idx]
      ? IMP_REVIEW[idx]
      : { included: it.action === "matched", note: "" };
  const included = rv.included;
  const steps =
    (it.steps_preview || []).join(" · ") || `${it.steps_count || 0} steps`;
  const reason = breakdownReason(it.breakdown);
  const controls =
    typeof idx === "number"
      ? `
    <div class="imp-review-controls" style="display:flex;gap:6px;align-items:center;margin-top:10px;flex-wrap:wrap">
      <button class="${included ? "go" : "ghost"}" style="padding:4px 10px;font-size:11px;margin:0"
        onclick="impSetRow(${idx}, true)">Include</button>
      <button class="${included ? "ghost" : "go"}" style="padding:4px 10px;font-size:11px;margin:0"
        onclick="impSetRow(${idx}, false)">Keep for later</button>
      <input type="text" placeholder="note (optional)" value="${esc(rv.note || "")}"
        oninput="impSetNote(${idx}, this.value)"
        style="flex:1;min-width:140px;font-size:11.5px;padding:4px 8px"/>
    </div>`
      : "";
  return `<div class="sheet-test-card ${included ? "included" : "pending"}">
    <div class="sheet-card-top">
      <div class="sheet-card-title">${esc(it.title || "(no title)")}</div>
      <span class="sheet-pill ${included ? "green" : "amber"}">${included ? "Included" : "Stored"}</span>
    </div>
    <div class="sheet-card-meta">
      <span class="sheet-pill">Source row ${esc(it.row_number || it.row_index + 1 || "")}</span>
      ${it.category ? `<span class="sheet-pill blue">${esc(it.category)}</span>` : ""}
      ${it.priority ? `<span class="sheet-pill ${String(it.priority).toLowerCase() === "high" ? "red" : "amber"}">${esc(it.priority)}</span>` : ""}
      ${it.endpoint ? `<span class="sheet-pill">${esc(it.method || "")} ${esc(it.endpoint)}</span>` : `<span class="sheet-pill">No endpoint</span>`}
    </div>
    <div class="sheet-detail-box">
      <b>Steps:</b> ${esc(steps)}<br>
      <b>Expected:</b> ${esc(it.expected_result || "As described in the imported row.")}
    </div>
    ${reason ? `<div class="sheet-reason"><b>Reason:</b> ${esc(reason)}</div>` : ""}
    ${controls}
  </div>`;
}

// Toggle one row's include/exclude decision and re-render just its pill/buttons.
window.impSetRow = function (idx, included) {
  if (!IMP_REVIEW[idx]) return;
  IMP_REVIEW[idx].included = !!included;
  const list = $("#imp-review-list");
  if (!list) return;
  const card = list.children[idx];
  if (card) {
    card.classList.toggle("included", included);
    card.classList.toggle("pending", !included);
    const pill = card.querySelector(".sheet-card-top .sheet-pill");
    if (pill) {
      pill.className = `sheet-pill ${included ? "green" : "amber"}`;
      pill.textContent = included ? "Included" : "Stored";
    }
    const btns = card.querySelectorAll(".imp-review-controls button");
    if (btns[0]) btns[0].className = included ? "go" : "ghost";
    if (btns[1]) btns[1].className = included ? "ghost" : "go";
  }
};
window.impSetNote = function (idx, val) {
  if (IMP_REVIEW[idx]) IMP_REVIEW[idx].note = val;
};

// Persist all decisions to the /review endpoint (idempotent per row).
window.impSaveReview = async function () {
  const { fid, iid } = IMP_REVIEW_CTX;
  if (!fid || !iid) {
    toast("Nothing to save", true);
    return;
  }
  const reviews = IMP_REVIEW.map((r) => ({
    project_imported_row_id: r.rid,
    identity_hash: r.hash,
    action: r.included ? "include" : "exclude",
    note: r.note || "",
  }));
  try {
    const r = await api(`/api/features/${fid}/tests/import/${iid}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviews }),
    });
    const d = r.data || {};
    toast(
      `Review saved · ${d.included || 0} included, ${d.excluded || 0} removed`,
    );
    if (typeof loadFeatures === "function") loadFeatures();
    if (fid && currentFeature === fid && typeof openFeature === "function") {
      setTimeout(() => openFeature(currentFeature), 300);
    }
  } catch (e) {
    toast(e.message, true);
  }
};

function breakdownReason(breakdown) {
  if (!breakdown || typeof breakdown !== "object") return "";
  const parts = [];
  if (breakdown.feature_anchor) parts.push("feature anchor matches");
  if (breakdown.route_family)
    parts.push("route family matches feature context");
  if (breakdown.intent_similarity)
    parts.push(
      `intent similarity ${(breakdown.intent_similarity || 0).toFixed ? breakdown.intent_similarity.toFixed(2) : breakdown.intent_similarity}`,
    );
  if (breakdown.title_similarity)
    parts.push(
      `title similarity ${(breakdown.title_similarity || 0).toFixed ? breakdown.title_similarity.toFixed(2) : breakdown.title_similarity}`,
    );
  return parts.join("; ");
}

// ---- Imported Sheet Library ----
window.openImportLibraryModal = async (fid) => {
  IMP_FID = fid || currentFeature || null;
  if (!IMP_FID) {
    toast("Open a feature first", true);
    return;
  }
  $("#implib-modal").classList.add("show");
  skIn("#implib-list", skeleton.rows(4, "Loading imported sheets"));
  $("#implib-stats").innerHTML = "";
  $("#implib-save").disabled = true;
  await loadImportLibrary();
};

async function runImplibRefresh() {
  const fid = IMP_FID || currentFeature;
  if (!fid) {
    toast("No feature in scope", true);
    return;
  }
  const btn = $("#implib-refresh");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Rescoring…";
  }
  try {
    const r = await api(`/api/features/${fid}/imported-sheets/refresh`, {
      method: "POST",
    });
    const d = r.data || {};
    toast(
      `Rescored ${d.rescored || 0} rows · auto-promoted ${d.newly_promoted || 0}`,
    );
    await loadImportLibrary();
    if (currentFeature === fid && typeof openFeature === "function")
      openFeature(currentFeature);
  } catch (e) {
    toast(e.message, true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Refresh / rescore";
    }
  }
}

async function loadImportLibrary() {
  const fid = IMP_FID || currentFeature;
  if (!fid) return;
  try {
    const r = await api(`/api/features/${fid}/imported-sheets`);
    IMPLIB_ITEMS = ((r.data || {}).imported_sheet_tests || []).sort(
      (a, b) =>
        String(a.original_filename || "").localeCompare(
          String(b.original_filename || ""),
        ) ||
        String(a.sheet || "").localeCompare(String(b.sheet || "")) ||
        (b.score || 0) - (a.score || 0),
    );
    IMPLIB_DESIRED = new Map(
      IMPLIB_ITEMS.map((it) => [it.identity_hash, !!it.is_in_feature]),
    );
    renderImplibList();
  } catch (e) {
    $("#implib-list").innerHTML = `<div class="err">${esc(e.message)}</div>`;
  }
}

function implibGroups() {
  const groups = new Map();
  for (const it of IMPLIB_ITEMS) {
    const key = `${it.feature_import_id || ""}::${it.original_filename || ""}::${it.sheet || ""}`;
    if (!groups.has(key))
      groups.set(key, {
        key,
        feature_import_id: it.feature_import_id || "",
        original_filename: it.original_filename || "",
        sheet: it.sheet || "",
        rows: [],
      });
    groups.get(key).rows.push(it);
  }
  return Array.from(groups.values());
}

function renderImplibList() {
  const groups = implibGroups();
  const rows = IMPLIB_ITEMS.length;
  const included = IMPLIB_ITEMS.filter((it) =>
    IMPLIB_DESIRED.get(it.identity_hash),
  ).length;
  const stored = rows - included;
  $("#implib-stats").innerHTML = sheetKpis([
    ["Sheets", groups.length, "green", "DOC"],
    ["Rows", rows, "purple", "GRID"],
    ["Included", included, "green", "OK"],
    ["Stored for later", stored, "amber", "BOX"],
  ]);
  $("#implib-loaded-count").textContent =
    `${rows} row${rows === 1 ? "" : "s"} loaded`;
  if (!rows) {
    $("#implib-list").innerHTML =
      `<div class="sheet-empty">No imported tests in this project yet. Upload a sheet from Import Sheet first.</div>`;
    $("#implib-save").disabled = true;
    return;
  }
  $("#implib-list").innerHTML = groups
    .map((g, idx) => renderImplibGroup(g, idx === 0))
    .join("");
  updateImplibSaveState();
}

function attr(v) {
  return esc(v || "")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderImplibGroup(g, open) {
  const included = g.rows.filter((it) =>
    IMPLIB_DESIRED.get(it.identity_hash),
  ).length;
  const total = g.rows.length;
  return `<details class="sheet-group" ${open ? "open" : ""}>
    <summary>
      <div class="sheet-group-main">
        <div class="sheet-icon">DOC</div>
        <div>
          <div class="sheet-group-title">${esc(g.original_filename || "Imported sheet")} ${g.sheet ? `<span class="sheet-pill blue">${esc(g.sheet)}</span>` : ""}</div>
          <div class="sheet-group-sub">${total} row${total === 1 ? "" : "s"} total · <span class="ok">${included} included</span></div>
        </div>
      </div>
      <div class="sheet-group-actions">
        <button class="sheet-danger-ghost" data-implib-action="remove-all" data-group="${attr(g.key)}" type="button"
          title="Remove every row of this sheet from THIS feature. The rows stay in the project library.">Remove all from feature</button>
        <button class="sheet-danger-ghost" data-implib-action="delete-sheet" data-feature-import-id="${attr(g.feature_import_id)}" data-filename="${attr(g.original_filename)}" data-sheet="${attr(g.sheet)}" type="button"
          title="Delete this sheet's rows from the WHOLE project library (all features). Cannot be undone.">Delete sheet from project</button>
        <span class="sheet-collapse">^</span>
      </div>
    </summary>
    <div class="sheet-group-body">${g.rows.map(renderImplibRow).join("")}</div>
  </details>`;
}

function renderImplibRow(it) {
  const desired = !!IMPLIB_DESIRED.get(it.identity_hash);
  const steps =
    (it.steps_preview || []).join(" · ") || `${it.steps_count || 0} steps`;
  return `<div class="sheet-test-card ${desired ? "included" : "pending"}">
    <div class="sheet-card-top">
      <div>
        <div class="sheet-card-title">${esc(it.title || "(no title)")}</div>
        <div class="muted">Source row ${esc(it.source_row_number || "")}</div>
      </div>
      <span class="sheet-pill ${desired ? "green" : ""}">${desired ? "Included" : "Available"}</span>
    </div>
    <div class="sheet-card-meta">
      ${it.category ? `<span class="sheet-pill blue">${esc(it.category)}</span>` : ""}
      ${it.priority ? `<span class="sheet-pill ${String(it.priority).toLowerCase() === "high" ? "red" : "amber"}">${esc(it.priority)}</span>` : ""}
      ${it.endpoint ? `<span class="sheet-pill">${esc(it.method || "")} ${esc(it.endpoint)}</span>` : ""}
      <span class="sheet-pill">Score ${(it.score || 0).toFixed(2)}</span>
    </div>
    <div class="sheet-detail-box">
      <b>Steps:</b> ${esc(steps)}<br>
      <b>Expected:</b> ${esc(it.expected_result || "As described in the imported row.")}
    </div>
    <div class="sheet-action-row">
      <button class="${desired ? "sheet-danger-ghost" : "sheet-primary"}" data-implib-action="${desired ? "toggle-remove" : "toggle-add"}" data-hash="${attr(it.identity_hash)}" type="button"
        title="${desired ? "Remove this test case from this feature (it stays in the project library)" : "Add this row to this feature as a test case"}">${desired ? "Remove from feature" : "Add to feature"}</button>
    </div>
  </div>`;
}

function updateImplibSaveState() {
  const changed = IMPLIB_ITEMS.some(
    (it) => !!it.is_in_feature !== !!IMPLIB_DESIRED.get(it.identity_hash),
  );
  $("#implib-save").disabled = !changed;
}

function handleImplibAction(el) {
  const action = el.dataset.implibAction;
  if (action === "toggle-add" || action === "toggle-remove") {
    const hash = el.dataset.hash;
    IMPLIB_DESIRED.set(hash, action === "toggle-add");
    renderImplibList();
  } else if (action === "remove-all") {
    const key = el.dataset.group;
    const group = implibGroups().find((g) => g.key === key);
    if (group)
      group.rows.forEach((it) => IMPLIB_DESIRED.set(it.identity_hash, false));
    renderImplibList();
  } else if (action === "delete-sheet") {
    implibDeleteSheet(
      el.dataset.featureImportId || "",
      el.dataset.filename || "",
      el.dataset.sheet || "",
    );
  }
}

async function saveImplibChanges() {
  const fid = IMP_FID || currentFeature;
  if (!fid) return;
  const add = IMPLIB_ITEMS.filter(
    (it) => !it.is_in_feature && IMPLIB_DESIRED.get(it.identity_hash),
  ).map((it) => it.identity_hash);
  const remove = IMPLIB_ITEMS.filter(
    (it) => it.is_in_feature && !IMPLIB_DESIRED.get(it.identity_hash),
  ).map((it) => it.identity_hash);
  if (!add.length && !remove.length) return;
  const btn = $("#implib-save");
  btn.disabled = true;
  btn.textContent = "Saving...";
  try {
    if (add.length) {
      await api(`/api/features/${fid}/imported-sheets/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identity_hashes: add }),
      });
    }
    if (remove.length) {
      await api(`/api/features/${fid}/imported-sheets/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identity_hashes: remove }),
      });
    }
    toast("Imported sheet changes saved");
    await loadImportLibrary();
    if (typeof openFeature === "function") openFeature(fid);
  } catch (e) {
    toast(e.message, true);
    updateImplibSaveState();
  } finally {
    btn.textContent = "Save changes";
  }
}

window.implibToggle = async (hash, add, deleteSystem = false) => {
  const fid = IMP_FID || currentFeature;
  if (!fid) return;
  const proceed = async () => {
    const url = `/api/features/${fid}/imported-sheets/${add ? "add" : "remove"}`;
    try {
      await api(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identity_hashes: [hash],
          delete_from_system: !!deleteSystem,
        }),
      });
      toast(
        add
          ? "Added to this feature"
          : deleteSystem
            ? "Deleted from imported library"
            : "Removed",
      );
      await loadImportLibrary();
      if ((add || deleteSystem) && typeof openFeature === "function")
        openFeature(currentFeature);
    } catch (e) {
      toast(e.message, true);
    }
  };
  if (deleteSystem) {
    openCaseConfirmation({
      title: "Delete imported test",
      copy: "Delete this imported test from the project library and every linked feature?",
      summary: "",
      confirmLabel: "Delete test",
      danger: true,
      onConfirm: proceed,
    });
  } else {
    await proceed();
  }
};

window.implibDeleteSheet = async (
  featureImportId,
  originalFilename,
  sheetName,
) => {
  const fid = IMP_FID || currentFeature;
  if (!fid) return;
  const label = `${originalFilename || "this upload"}${sheetName ? ` · ${sheetName}` : ""}`;
  openCaseConfirmation({
    title: "Delete imported sheet",
    copy: `Permanently delete ${label}?`,
    summary: `<div style="color:var(--red);font-weight:600;margin-top:4px">This will delete all imported test cases from this sheet across every feature in this project.</div>`,
    confirmLabel: "Delete sheet",
    danger: true,
    onConfirm: async () => {
      await api(`/api/features/${fid}/imported-sheets/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          delete_from_system: true,
          feature_import_id: featureImportId || null,
          original_filename: originalFilename || null,
          sheet_name: sheetName || null,
        }),
      });
      toast("Deleted imported sheet permanently");
      await loadImportLibrary();
      if (typeof openFeature === "function") openFeature(currentFeature);
    },
  });
};

