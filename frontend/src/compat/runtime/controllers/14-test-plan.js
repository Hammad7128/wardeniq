// ---- Test Plan ----
async function initTestPlan() {
  if (!currentFeature) {
    $("#tp-no-feature").style.display = "block";
    $("#tp-workspace").style.display = "none";
    return;
  }
  $("#tp-no-feature").style.display = "none";
  $("#tp-workspace").style.display = "block";
  $("#tp-feat-title").textContent =
    `${$("#d-name").textContent || "Feature"} — Test Plan`;
  $("#tp-content").innerHTML = skeletonState(
    `<div style="display:grid;gap:18px">${skeleton.blockLines(5)}${skeleton.blockLines(4)}</div>`,
    "Loading test plan",
  );
  $("#tp-content").style.display = "block";
  $("#tp-progress").style.display = "block";
  $("#tp-bar").style.width = "30%";
  $("#tp-status").textContent = "Loading test plan status...";
  $("#tp-generate-btn").style.display = "none";
  $("#tp-export-csv").style.display = "none";
  $("#tp-export-pdf").style.display = "none";

  try {
    const res = await api(`/api/features/${currentFeature}/test-plan/latest`);
    const run = res.run;
    if (!run) {
      $("#tp-progress").style.display = "none";
      $("#tp-content").innerHTML = "";
      $("#tp-content").style.display = "none";
      $("#tp-status").textContent = "No test plan generated yet.";
      $("#tp-generate-btn").style.display = "inline-block";
      $("#tp-generate-btn").disabled = false;
    } else if (run.status === "COMPLETED") {
      $("#tp-progress").style.display = "none";
      $("#tp-status").textContent = "";
      $("#tp-content").innerHTML = renderTestPlan(run.content);
      $("#tp-content").style.display = "block";
      $("#tp-export-csv").href = `/api/test-plan/runs/${run.id}/export/csv`;
      $("#tp-export-csv").style.display = "inline-block";
      $("#tp-export-pdf").href = `/api/test-plan/runs/${run.id}/export/pdf`;
      $("#tp-export-pdf").style.display = "inline-block";
    } else if (run.status === "PROCESSING") {
      watchTestPlanStream(run.id);
    } else {
      $("#tp-progress").style.display = "none";
      $("#tp-content").innerHTML = "";
      $("#tp-content").style.display = "none";
      $("#tp-status").innerHTML =
        `<span class="err">Previous generation failed.</span>`;
      $("#tp-generate-btn").style.display = "inline-block";
      $("#tp-generate-btn").disabled = false;
    }
  } catch (e) {
    $("#tp-progress").style.display = "none";
    $("#tp-content").innerHTML = "";
    $("#tp-content").style.display = "none";
    $("#tp-status").innerHTML = `<span class="err">${esc(e.message)}</span>`;
  }
}

$("#tp-generate-btn").onclick = async () => {
  if (!currentFeature) return;
  $("#tp-generate-btn").disabled = true;
  $("#tp-status").textContent = "Initializing test plan run...";
  $("#tp-progress").style.display = "block";
  $("#tp-bar").style.width = "20%";

  try {
    const res = await api(`/api/features/${currentFeature}/test-plan`, {
      method: "POST",
    });
    watchTestPlanStream(res.runId);
  } catch (e) {
    $("#tp-progress").style.display = "none";
    $("#tp-status").innerHTML = `<span class="err">${esc(e.message)}</span>`;
    $("#tp-generate-btn").disabled = false;
  }
};

function watchTestPlanStream(runId) {
  $("#tp-progress").style.display = "block";
  $("#tp-bar").style.width = "30%";
  $("#tp-status").textContent = "Synthesizing test plan via LLM...";
  $("#tp-content").style.fontFamily = "inherit";
  $("#tp-content").innerHTML = skeletonState(
    `<div style="display:grid;gap:18px">${skeleton.blockLines(5)}${skeleton.blockLines(4)}${skeleton.blockLines(6)}</div>`,
    "Generating test plan",
  );
  $("#tp-content").style.display = "block";
  $("#tp-generate-btn").style.display = "none";
  $("#tp-export-csv").style.display = "none";
  $("#tp-export-pdf").style.display = "none";

  const es = new EventSource(`/api/test-plan/runs/${runId}/stream`);
  es.addEventListener("status", (e) => {
    const payload = JSON.parse(e.data);
    if (payload.status === "COMPLETED") {
      es.close();
      $("#tp-progress").style.display = "none";
      $("#tp-status").textContent = "Completed";
      $("#tp-content").style.fontFamily = "monospace";
      $("#tp-content").innerHTML = renderTestPlan(payload.testPlan);
      $("#tp-content").style.display = "block";
      $("#tp-export-csv").href = `/api/test-plan/runs/${runId}/export/csv`;
      $("#tp-export-csv").style.display = "inline-block";
      $("#tp-export-pdf").href = `/api/test-plan/runs/${runId}/export/pdf`;
      $("#tp-export-pdf").style.display = "inline-block";
    } else if (payload.status === "FAILED") {
      es.close();
      $("#tp-progress").style.display = "none";
      $("#tp-content").innerHTML = "";
      $("#tp-content").style.display = "none";
      $("#tp-status").innerHTML =
        `<span class="err">Failed to generate test plan.</span>`;
      $("#tp-generate-btn").style.display = "inline-block";
      $("#tp-generate-btn").disabled = false;
    } else {
      $("#tp-bar").style.width = "60%";
      $("#tp-status").textContent = "Synthesizing sections via LLM...";
    }
  });
  es.addEventListener("done", () => es.close());
  es.addEventListener("error", () => {
    es.close();
    $("#tp-progress").style.display = "none";
    $("#tp-status").innerHTML =
      `<span class="err">Connection lost. Re-checking...</span>`;
    setTimeout(initTestPlan, 2000);
  });
}

function renderTestPlan(plan) {
  if (!plan || !plan.sections) return "";
  let html = "";
  const meta = plan.meta || {};
  html += `<h1>${esc(meta.featureName || "Test Plan")}</h1>`;
  if (meta.projectName) {
    html += `<div class="muted" style="margin-bottom:15px">Project: ${esc(meta.projectName)} · Version: ${esc(meta.featureVersionNumber)}</div>`;
  }

  plan.sections.forEach((sec) => {
    html += `<h2 style="color:var(--accent2);margin-top:20px;border-bottom:1px solid var(--line);padding-bottom:5px">${esc(sec.title)}</h2>`;
    const type = sec.type;
    const content = sec.content;

    if (type === "paragraph") {
      html += `<p>${esc(content)}</p>`;
    } else if (type === "bullets" || type === "checklist") {
      if (Array.isArray(content)) {
        html += `<ul style="padding-left:20px;margin:8px 0">${content.map((x) => `<li style="margin:4px 0">${esc(x)}</li>`).join("")}</ul>`;
      }
    } else if (type === "key_value") {
      if (Array.isArray(content)) {
        html +=
          `<table style="margin-top:10px">` +
          content
            .map(
              (x) =>
                `<tr><td style="font-weight:600;width:180px">${esc(x.key)}</td><td>${esc(x.value)}</td></tr>`,
            )
            .join("") +
          `</table>`;
      }
    } else if (type === "grouped_list") {
      if (content && typeof content === "object") {
        if (content.in_scope && content.in_scope.length) {
          html +=
            `<h3 style="font-size:13px;margin:10px 0 4px">In Scope:</h3><ul style="padding-left:20px;margin-bottom:8px">` +
            content.in_scope
              .map((x) => `<li style="margin:4px 0">${esc(x)}</li>`)
              .join("") +
            `</ul>`;
        }
        if (content.out_of_scope && content.out_of_scope.length) {
          html +=
            `<h3 style="font-size:13px;margin:10px 0 4px">Out of Scope:</h3><ul style="padding-left:20px;margin-bottom:8px">` +
            content.out_of_scope
              .map((x) => `<li style="margin:4px 0">${esc(x)}</li>`)
              .join("") +
            `</ul>`;
        }
      }
    } else if (type === "table") {
      if (content && typeof content === "object") {
        const columns = content.columns || [];
        const rows = content.rows || [];
        html +=
          `<table style="margin-top:10px"><thead><tr>` +
          columns.map((c) => `<th>${esc(c)}</th>`).join("") +
          `</tr></thead><tbody>`;
        rows.forEach((r) => {
          if (Array.isArray(r)) {
            html +=
              `<tr>` +
              r.map((cell) => `<td>${esc(cell)}</td>`).join("") +
              `</tr>`;
          } else if (r && typeof r === "object") {
            html +=
              `<tr>` +
              columns.map((c) => `<td>${esc(r[c] || "")}</td>`).join("") +
              `</tr>`;
          }
        });
        html += `</tbody></table>`;
      }
    } else {
      html += `<pre>${esc(JSON.stringify(content, null, 2))}</pre>`;
    }
  });
  return html;
}

