// ---- step library CRUD ----
let STEP_MODAL_MODE = "create";
let STEP_MODAL_ID = null;

setTimeout(() => {
  const newBtn = document.getElementById("s-new");
  if (newBtn) {
    newBtn.onclick = () => {
      STEP_MODAL_MODE = "create";
      STEP_MODAL_ID = null;

      $("#step-modal-heading").textContent = "Create Step";
      $("#step-modal-prefix").value = "Given";
      $("#step-modal-action").value = "";
      $("#step-modal-expected").value = "";
      $("#step-modal-warn").style.display = "none";
      $("#step-modal").classList.add("show");
    };
  }

  if ($("#step-modal-close")) {
    $("#step-modal-close").onclick = $("#step-modal-cancel").onclick = () => {
      $("#step-modal").classList.remove("show");
    };
  }

  if ($("#step-modal-save")) {
    $("#step-modal-save").onclick = async () => {
      const prefix = $("#step-modal-prefix").value;
      const rawAction = $("#step-modal-action").value.trim();
      const expected = $("#step-modal-expected").value.trim();

      if (!rawAction) {
        toast("Action / Description is required", true);
        return;
      }

      const action = prefix ? `${prefix} ${rawAction}` : rawAction;
      const saveBtn = $("#step-modal-save");
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving…";

      try {
        if (STEP_MODAL_MODE === "create") {
          await api("/api/steps", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, expected }),
          });
          toast("Step created ✓");
        } else {
          const r = await api("/api/steps/" + STEP_MODAL_ID, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action, expected }),
          });
          toast(`Updated — affects ${r.affected_cases} case(s) ✓`);

          if (SELECTED_STEP_ID === STEP_MODAL_ID) {
            setTimeout(() => showStepDetails(STEP_MODAL_ID), 200);
          }
        }
        $("#step-modal").classList.remove("show");
        loadSteps();
      } catch (e) {
        toast(e.message, true);
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save";
      }
    };
  }
}, 500);

window.editStepFromMap = (id) => {
  const s = STEPMAP[id];
  if (!s) return;

  STEP_MODAL_MODE = "edit";
  STEP_MODAL_ID = id;

  $("#step-modal-heading").textContent = "Edit Step";

  const detectedPrefix = getStepType(s.action);
  let prefix = "";
  if (["given", "when", "then", "and"].includes(detectedPrefix)) {
    prefix = s.action.split(" ")[0];
  }
  $("#step-modal-prefix").value = prefix;
  $("#step-modal-action").value = getStepBase(s.action);
  $("#step-modal-expected").value = s.expected || "";

  const warnDiv = $("#step-modal-warn");
  if (s.used_in_cases > 0) {
    warnDiv.textContent = `Warning: This step is referenced by ${s.used_in_cases} active testcase(s). Updating it will immediately affect all of them.`;
    warnDiv.style.display = "block";
  } else {
    warnDiv.style.display = "none";
  }

  $("#step-modal").classList.add("show");
};

window.editStepLib = (id, a, e) => {
  editStepFromMap(id);
};

window.delStepLib = async (id) => {
  const s = STEPMAP[id];
  if (!s) return;

  if (s.used_in_cases > 0) {
    toast(
      `Cannot delete: Step is referenced by ${s.used_in_cases} case(s).`,
      true,
    );
    return;
  }

  try {
    const r = await api("/api/steps/" + id, { method: "DELETE" });
    if (r.deleted) {
      if (SELECTED_STEP_ID === id) {
        $("#s-detail-pane").style.display = "none";
        SELECTED_STEP_ID = null;
      }
      loadSteps();
      toast("Step deleted");
    } else {
      toast(r.reason, true);
    }
  } catch (e) {
    toast(e.message, true);
  }
};

// ---- new / delete test case ----
$("#tc-new").onclick = () => {
  const fid = $("#tc-feat").value;
  if (!fid) {
    toast("Pick a Feature filter first, so the new case is added to it", true);
    return;
  }
  editing = {
    id: null,
    feature_id: fid,
    shared_with_features: 0,
    steps: [{ action: "", expected: "" }],
  };
  $("#m-heading").textContent = "Create test case";
  $("#m-title").value = "";
  $("#m-type").value = "functional";
  $("#m-prio").value = "Medium";
  $("#m-pre").value = "";
  $("#m-tags").value = "";
  $("#m-warn").textContent =
    "The testcase will be linked to the selected feature.";
  $("#m-del").style.display = "none";
  renderSteps();
  $("#m-msg").textContent = "";
  $("#modal").classList.add("show");
};
window.requestDeleteCase = async (cid, known) => {
  let c = known;
  try {
    if (!c) c = await api("/api/test-cases/" + cid);
  } catch (e) {
    toast(e.message, true);
    return;
  }
  const links = c.shared_with_features || 0;
  const casesViewOpen = !$("#view-cases").hidden;
  const scopedFeature = casesViewOpen
    ? $("#tc-feat").value
    : currentFeature || "";
  const scopedLink = (c.features || []).find(
    (feature) => feature.id === scopedFeature,
  );
  const refreshAfterDelete = () => {
    $("#modal").classList.remove("show");
    loadCases();
    if (currentFeature) openFeature(currentFeature);
  };
  if (scopedLink) {
    const inherited = [
      "reused",
      "carried",
      "carried_repaired",
      "inherited",
      "adapted",
    ].includes(scopedLink.origin);
    openCaseConfirmation({
      title: "Remove testcase from this feature",
      copy:
        links > 1
          ? `This removes “${c.title}” only from ${scopedLink.name}. Its ${links - 1} other feature link${links - 1 === 1 ? "" : "s"} will stay intact.`
          : `This is the testcase's only feature link, so removing it from ${scopedLink.name} will also remove the orphaned testcase.`,
      summary: `<b>${esc(c.display_id || "")} ${esc(c.title)}</b><div class="muted" style="margin-top:6px">${inherited ? "Inherited / reused here" : "Created here"} · linked to ${links} feature${links === 1 ? "" : "s"}</div>`,
      confirmLabel: `Remove from ${scopedLink.name}`,
      onConfirm: async () => {
        await api(`/api/features/${scopedFeature}/test-cases/${cid}`, {
          method: "DELETE",
        });
        refreshAfterDelete();
        toast(
          links > 1
            ? "Removed from this feature; other links were preserved"
            : "Testcase removed",
        );
      },
      secondaryLabel: links > 1 ? "Delete everywhere" : null,
      onSecondary:
        links > 1
          ? async () => {
              await api(`/api/test-cases/${cid}?force=true`, {
                method: "DELETE",
              });
              refreshAfterDelete();
              toast("Testcase deleted from every feature");
            }
          : null,
    });
    return;
  }
  openCaseConfirmation({
    title: "Delete testcase",
    copy:
      links > 1
        ? `This is a global delete. “${c.title}” will be removed from all ${links} linked features.`
        : `“${c.title}” will be permanently deleted.`,
    summary: `<b>${esc(c.title)}</b><div class="muted" style="margin-top:6px">${links} feature link${links === 1 ? "" : "s"} · ${(c.steps || []).length} step${(c.steps || []).length === 1 ? "" : "s"}</div>`,
    confirmLabel: links > 1 ? "Delete from all features" : "Delete testcase",
    danger: true,
    onConfirm: async () => {
      await api(`/api/test-cases/${cid}${links > 1 ? "?force=true" : ""}`, {
        method: "DELETE",
      });
      refreshAfterDelete();
      toast("Testcase deleted");
    },
  });
};

// ---- feature delete / rename ----
$("#d-del").onclick = async () => {
  if (!currentFeature) return;
  const featureId = currentFeature;
  openCaseConfirmation({
    title: "Delete feature",
    copy: "This removes the feature, its document chunks, and its testcase links. Testcases still linked to another feature will not be deleted.",
    summary: `<b>${esc($("#d-name").textContent)}</b><div class="muted" style="margin-top:6px">${esc($("#d-meta").textContent)}</div>`,
    confirmLabel: "Delete feature",
    danger: true,
    onConfirm: async () => {
      const r = await api("/api/features/" + featureId, { method: "DELETE" });
      currentFeature = null;
      showFeatureList();
      loadFeatures();
      refreshStatus();
      toast(
        `Feature deleted · ${r.removed_orphan_cases} orphan testcase(s) removed · ${r.preserved_shared_cases} shared testcase(s) preserved`,
      );
    },
  });
};
$("#d-rename").onclick = async () => {
  if (!currentFeature) return;
  const name = await uiPrompt(
    "Rename feature",
    "Feature name",
    $("#d-name").textContent,
  );
  if (!name) return;
  await api("/api/features/" + currentFeature, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  openFeature(currentFeature);
  loadFeatures();
  toast("Renamed");
};
// ---- new version ----
$("#d-newver").onclick = () => {
  if (!currentFeature) return;
  $("#vm-feat").textContent =
    `${$("#d-name").textContent} — current ${$("#d-version").selectedOptions[0]?.textContent || ""}`;
  $("#vm-file").value = "";
  $("#vm-text").value = "";
  if ($("#vm-confluence")) $("#vm-confluence").value = "";
  if ($("#vm-figma")) $("#vm-figma").value = "";
  $("#vm-replace").checked = false;
  $("#vm-msg").textContent = "";
  $("#vmodal").classList.add("show");
};
if ($("#d-reuse-imports"))
  $("#d-reuse-imports").onclick = () => {
    if (!currentFeature) {
      toast("Open a feature first", true);
      return;
    }
    openImportLibraryModal(currentFeature);
  };
$("#vm-cancel").onclick = () => $("#vmodal").classList.remove("show");
$("#vm-go").onclick = async () => {
  const splitLinks = (el) =>
    ((el && el.value) || "")
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  const vConfl = splitLinks($("#vm-confluence"));
  const vFigma = splitLinks($("#vm-figma"));
  if (
    !$("#vm-file").files.length &&
    !$("#vm-text").value.trim() &&
    !vConfl.length &&
    !vFigma.length
  ) {
    $("#vm-msg").innerHTML =
      `<span class="err">Upload a doc, paste text, or add a Confluence/Figma link.</span>`;
    return;
  }
  $("#vm-go").disabled = true;
  $("#vm-msg").textContent = "uploading + diffing against previous version…";
  const fd = new FormData();
  for (const f of $("#vm-file").files) fd.append("files", f);
  fd.append("text", $("#vm-text").value);
  fd.append("replace", $("#vm-replace").checked ? "true" : "false");
  vConfl.forEach((u) => fd.append("confluence_url", u));
  vFigma.forEach((u) => fd.append("figma_url", u));
  try {
    const r = await api(`/api/features/${currentFeature}/versions`, {
      method: "POST",
      body: fd,
    });
    const d = r.diff || {};
    $("#vm-msg").innerHTML =
      `<span class="ok">v${r.version} created — ${d.kept || 0} kept${d.retired && d.retired.length ? `, ${d.retired.length} retired` : ""}. Generating new cases…</span>`;
    toast(`Version ${r.version} created`);
    setTimeout(() => {
      $("#vmodal").classList.remove("show");
      openFeature(r.feature_id).then(() =>
        watchFeatureGen(r.job_id, r.feature_id),
      );
      loadFeatures();
    }, 1200);
  } catch (e) {
    $("#vm-msg").innerHTML = `<span class="err">${esc(e.message)}</span>`;
  } finally {
    $("#vm-go").disabled = false;
  }
};

