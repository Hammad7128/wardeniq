// ---- steps ----
let ALL_STEPS = [];
let STEPMAP = {};
let SELECTED_STEP_ID = null;

async function loadSteps() {
  if (!document.getElementById("s-list-body")) return;
  skIn("#s-list-body", skeleton.rows(8, "Loading step library"));
  try {
    const r = await api("/api/steps?limit=1000");
    ALL_STEPS = r.steps || [];
    $("#s-count").textContent = `(${ALL_STEPS.length})`;
    STEPMAP = {};
    ALL_STEPS.forEach((s) => (STEPMAP[s.id] = s));
    renderStepList();
  } catch (e) {
    $("#s-list-body").innerHTML =
      `<div class="err" style="padding:18px">Couldn't load steps. ${esc(e.message)}</div>`;
  }
}

function getStepType(action) {
  const clean = (action || "").trim().toLowerCase();
  if (clean.startsWith("given ")) return "given";
  if (clean.startsWith("when ")) return "when";
  if (clean.startsWith("then ")) return "then";
  if (clean.startsWith("and ") || clean.startsWith("but ")) return "and";
  return "other";
}

function getStepBase(action) {
  const clean = (action || "").trim();
  const lower = clean.toLowerCase();
  if (lower.startsWith("given ")) return clean.slice(6).trim();
  if (lower.startsWith("when ")) return clean.slice(5).trim();
  if (lower.startsWith("then ")) return clean.slice(5).trim();
  if (lower.startsWith("and ")) return clean.slice(4).trim();
  if (lower.startsWith("but ")) return clean.slice(4).trim();
  return clean;
}

function renderStepList() {
  const tbody = $("#s-list-body");
  if (!tbody) return;

  const searchVal = $("#s-search").value.trim().toLowerCase();
  const typeFilter = $("#s-filter-type").value;
  const usageFilter = $("#s-filter-usage").value;

  const filtered = ALL_STEPS.filter((s) => {
    if (searchVal) {
      const inAction = (s.action || "")
        .toLowerCase()
        .includes(searchVal);

      const inExpected = (s.expected || "")
        .toLowerCase()
        .includes(searchVal);

      if (!inAction && !inExpected) {
        return false;
      }
    }

    const detectedType = getStepType(s.action);

    if (typeFilter) {
      if (typeFilter === "Other") {
        if (
          ["given", "when", "then", "and"].includes(
            detectedType,
          )
        ) {
          return false;
        }
      } else if (typeFilter === "And") {
        if (detectedType !== "and") {
          return false;
        }
      } else if (
        detectedType !== typeFilter.toLowerCase()
      ) {
        return false;
      }
    }

    if (usageFilter) {
      if (
        usageFilter === "used" &&
        s.used_in_cases === 0
      ) {
        return false;
      }

      if (
        usageFilter === "unused" &&
        s.used_in_cases > 0
      ) {
        return false;
      }
    }

    return true;
  });

  const KW = {
    given: "Given",
    when: "When",
    then: "Then",
  };

  tbody.innerHTML =
    filtered
      .map((s) => {
        const t = getStepType(s.action);

        const isSelected =
          SELECTED_STEP_ID === s.id
            ? " selected"
            : "";

        const kw = KW[t];

        const kwHtml = kw
          ? `<span class="step-kw ${t}">${kw}</span>`
          : "";

        let base = getStepBase(s.action);

        if (!kw && base) {
          base =
            base.charAt(0).toUpperCase() +
            base.slice(1);
        }

        const actionText = esc(base);

        const expected = (
          s.expected || ""
        ).trim();

        const used = s.used_in_cases;

        const usageHtml =
          used > 0
            ? `
              <span
                class="step-usage"
                title="Used in ${used} test case${used === 1 ? "" : "s"}"
              >
                ${used} case${used === 1 ? "" : "s"}
              </span>
            `
            : `
              <span
                class="step-usage unused"
                title="Not referenced by any test case yet"
              >
                Unused
              </span>
            `;

        return `
          <div
            class="step-item${isSelected}"
            onclick="selectStepRow(event, '${s.id}')"
          >
            <div class="step-item-main">

              <div class="step-line">
                ${kwHtml}

                <span class="step-text">
                  ${actionText}
                </span>
              </div>

              ${
                expected
                  ? `
                    <div class="step-expected">
                      <span class="step-exp-label">
                        Expected
                      </span>

                      <span>
                        ${esc(expected)}
                      </span>
                    </div>
                  `
                  : ""
              }

            </div>

            <div
              class="step-item-meta"
              onclick="event.stopPropagation()"
            >
              ${usageHtml}

              <div class="step-actions">

                <!-- EDIT -->
                <button
                  type="button"
                  class="step-act-btn step-edit-btn"
                  title="Edit step"
                  aria-label="Edit step"
                  onclick="editStepFromMap('${s.id}')"
                >
                  <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path d="M12 20h9"></path>

                    <path
                      d="M16.5 3.5a2.12 2.12 0 0 1 3 3L8 18l-4 1 1-4Z"
                    ></path>
                  </svg>
                </button>

                <!-- DELETE -->
                <button
                  type="button"
                  class="step-act-btn step-delete-btn"
                  title="Delete step"
                  aria-label="Delete step"
                  onclick="delStepLib('${s.id}')"
                >
                  <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18"></path>

                    <path d="M8 6V4h8v2"></path>

                    <path
                      d="M19 6l-1 14H6L5 6"
                    ></path>

                    <path d="M10 11v5"></path>
                    <path d="M14 11v5"></path>
                  </svg>
                </button>

              </div>
            </div>
          </div>
        `;
      })
      .join("") ||
    `
      <div class="step-library-empty">
        <div class="step-library-empty-icon">
          <svg
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7"></circle>
            <path d="m20 20-4-4"></path>
          </svg>
        </div>

        <strong>No matching steps</strong>

        <span>
          Try changing your search or filters.
        </span>
      </div>
    `;
}

window.selectStepRow = (event, id) => {
  SELECTED_STEP_ID = id;
  const rows = $("#s-list-body").querySelectorAll(".step-item");
  rows.forEach((r) => r.classList.remove("selected"));
  const row = event.currentTarget;
  if (row) row.classList.add("selected");
  showStepDetails(id);
};

window.showStepDetails = async (id) => {
  const s = STEPMAP[id];
  if (!s) return;
  const pane = $("#s-detail-pane");
  if (!pane) return;
  pane.style.display = "flex";
  const t = getStepType(s.action);
  const label =
    t === "other" ? "Action" : t === "and" ? "And/But" : t.toUpperCase();
  $("#s-detail-type").innerHTML =
    `<span class="step-badge ${t}">${esc(label)}</span>`;
  $("#s-detail-action").textContent = getStepBase(s.action);
  $("#s-detail-expected").textContent =
    s.expected || "No separate expected result defined.";
  const listDiv = $("#s-detail-cases-list");
  listDiv.innerHTML = loadingRow("Loading cases…");
  try {
    const res = await api(`/api/test-cases?step_id=${id}&limit=200`);
    const cases = res.items || [];
    $("#s-detail-cases-title").textContent = `Used in Cases (${cases.length})`;
    listDiv.innerHTML =
      cases
        .map(
          (c) => `
      <div class="stepitem" style="font-size:12.5px;padding:6px 8px;background:rgba(255,255,255,0.02);border:1px solid #1E2A40;border-radius:6px;display:flex;justify-content:space-between;align-items:center;gap:10px">
        <span style="font-weight:500;color:#e2e8f0">${c.display_id ? `<code style="font-size:10.5px;background:rgba(255,255,255,.06);padding:1px 5px;border-radius:3px;margin-right:6px;color:#94a3b8">${esc(c.display_id)}</code>` : ""}${esc(c.title)}</span>
        <button class="ghost" style="padding:2px 6px;font-size:11px" onclick="openAndGoToCase('${c.id}', '${c.feature_id}')">Open ↗</button>
      </div>
    `,
        )
        .join("") ||
      `<span class="muted" style="font-size:12px">Not referenced by any active test cases.</span>`;
  } catch (e) {
    listDiv.innerHTML = `<span class="err" style="font-size:12px">${esc(e.message)}</span>`;
  }
};

window.openAndGoToCase = async (caseId, featureId) => {
  await openFeature(featureId);
  navigateTo("features");
  setTimeout(() => {
    viewCase(caseId);
    const el = document.querySelector(`[data-case-item="${caseId}"]`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, 300);
};

// Bind UI event handlers
setTimeout(() => {
  if ($("#s-search")) $("#s-search").oninput = renderStepList;
  if ($("#s-filter-type")) $("#s-filter-type").onchange = renderStepList;
  if ($("#s-filter-usage")) $("#s-filter-usage").onchange = renderStepList;
  if ($("#s-detail-close")) {
    $("#s-detail-close").onclick = () => {
      $("#s-detail-pane").style.display = "none";
      SELECTED_STEP_ID = null;
      const rows = $("#s-list-body").querySelectorAll(".step-item");
      rows.forEach((r) => r.classList.remove("selected"));
    };
  }
}, 500);

