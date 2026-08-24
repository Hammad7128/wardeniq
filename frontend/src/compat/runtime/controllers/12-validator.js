// ---- MCQ Validator ----
let validatorAnswers = {};
// Load existing validator state ONLY — never triggers generation.
// Generation happens on the "Generate Validator" / "Retake Validator" buttons (runValidator).
async function initValidator() {
  if (!currentFeature) {
    $("#val-no-feature").style.display = "block";
    $("#val-workspace").style.display = "none";
    return;
  }
  $("#val-no-feature").style.display = "none";
  $("#val-workspace").style.display = "block";
  $("#val-feat-title").textContent =
    `${$("#d-name").textContent || "Feature"} — MCQ Validator`;
  $("#val-results").style.display = "none";
  skIn("#val-qa-container", skeleton.cards(3, "Loading validator"));
  $("#val-progress").style.display = "none";
  $("#val-log").style.display = "none";
  $("#val-generate-btn").style.display = "none";
  $("#val-retake-btn").style.display = "none";
  $("#val-status").textContent = "Loading validator...";

  try {
    const res = await api(`/api/features/${currentFeature}/validator/latest`);
    if (!res || res.mode === "none") {
      $("#val-qa-container").innerHTML = "";
      $("#val-status").textContent = "No validator generated yet.";
      $("#val-generate-btn").style.display = "inline-block";
      $("#val-generate-btn").disabled = false;
      return;
    }
    currentRunId = res.run && res.run.id;
    if (res.mode === "generating") {
      watchValidatorJob(res.run && res.run.job_id);
      return;
    }
    $("#val-qa-container").innerHTML = "";
    $("#val-status").textContent = "";
    $("#val-retake-btn").style.display = "inline-block";
    $("#val-retake-btn").disabled = false;
    if (res.mode === "score") {
      renderValidatorResults(res.score);
    } else {
      validatorAnswers = {};
      if (res.answers && res.answers.length) {
        res.answers.forEach((a) => {
          validatorAnswers[a.question_id] = {
            selectedIndex: a.selected_index,
            confidence: a.confidence,
            comment: a.comment || "",
          };
        });
      }
      renderValidatorQuestions(res.questions);
    }
  } catch (e) {
    $("#val-progress").style.display = "none";
    $("#val-qa-container").innerHTML = "";
    $("#val-status").innerHTML = `<span class="err">${esc(e.message)}</span>`;
  }
}

// Trigger validator generation (button-driven).
async function runValidator(forceNew = false) {
  if (!currentFeature) return;
  $("#val-results").style.display = "none";
  $("#val-generate-btn").style.display = "none";
  $("#val-retake-btn").disabled = true;
  skIn(
    "#val-qa-container",
    skeleton.cards(3, "Generating validator questions"),
  );
  $("#val-progress").style.display = "block";
  $("#val-bar").style.width = "40%";
  $("#val-status").textContent = "Loading validator...";

  try {
    const res = await api(`/api/features/${currentFeature}/validator`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ forceNew: forceNew }),
    });
    currentRunId = res.run && res.run.id;
    if (res.mode === "generating") {
      watchValidatorJob(res.job_id || (res.run && res.run.job_id));
      return;
    }
    // An existing run was returned directly — reload the view to render it.
    initValidator();
  } catch (e) {
    $("#val-progress").style.display = "none";
    $("#val-qa-container").innerHTML = "";
    $("#val-status").innerHTML = `<span class="err">${esc(e.message)}</span>`;
    $("#val-generate-btn").style.display = "inline-block";
    $("#val-generate-btn").disabled = false;
  }
}

function watchValidatorJob(jobId) {
  $("#val-progress").style.display = "block";
  $("#val-log").style.display = "block";
  $("#val-status").textContent = "Generating validator questions…";
  if (!jobId) {
    setTimeout(() => initValidator(), 1500);
    return;
  }
  watchJob(jobId, (j) => {
    $("#val-bar").style.width = (j.progress || 5) + "%";
    renderJobLog("#val-log", j);
    $("#val-status").textContent =
      j.status === "running" ? j.stage || "Generating…" : "";
    if (j.status === "succeeded") initValidator();
    if (j.status === "failed") {
      $("#val-progress").style.display = "none";
      $("#val-log").style.display = "none";
      $("#val-qa-container").innerHTML = "";
      $("#val-status").innerHTML =
        `<span class="err">${esc(j.error || "Validator generation failed")}</span>`;
      $("#val-generate-btn").style.display = "inline-block";
      $("#val-generate-btn").disabled = false;
    }
  });
}

$("#val-generate-btn").onclick = () => runValidator(false);

function renderValidatorQuestions(questions) {
  let html = "";
  questions.forEach((q, idx) => {
    const qId = q.id;
    validatorAnswers[qId] = validatorAnswers[qId] || {
      selectedIndex: null,
      confidence: 3,
      comment: "",
    };
    const optionsHtml = q.options
      .map((opt, oIdx) => {
        return `<button class="val-opt" data-qid="${qId}" data-oidx="${oIdx}" id="opt-${qId}-${oIdx}" onclick="selectValOption('${qId}', ${oIdx})">${esc(opt)}</button>`;
      })
      .join("");

    html += `
    <div class="val-qcard" id="qcard-${qId}">
      <div class="category">${esc(q.category.replace("_", " "))}</div>
      <div class="qtext">${idx + 1}. ${esc(q.question)}</div>
      <div class="val-opts">${optionsHtml}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;gap:12px;flex-wrap:wrap">
        <div class="val-conf-row" style="margin:0">
          <span style="font-size:12.5px;color:var(--muted)">Confidence:</span>
          ${[1, 2, 3, 4, 5].map((lvl) => `<button class="val-conf-btn" id="conf-${qId}-${lvl}" onclick="selectValConfidence('${qId}', ${lvl})">${lvl}</button>`).join("")}
        </div>
        <div style="flex:1;min-width:180px">
          <input placeholder="Clarifying comment (optional)…" id="comment-${qId}" onchange="updateValComment('${qId}', this.value)" style="padding:6px 10px;font-size:12.5px"/>
        </div>
      </div>
    </div>`;
  });
  html += `<button class="go" id="val-submit-btn" style="width:100%;margin-top:20px" onclick="submitValidatorAnswers()">Submit Answers</button>`;
  $("#val-qa-container").innerHTML = html;

  questions.forEach((q) => {
    const qId = q.id;
    const ans = validatorAnswers[qId];
    if (ans.selectedIndex !== null) selectValOption(qId, ans.selectedIndex);
    selectValConfidence(qId, ans.confidence);
    $(`#comment-${qId}`).value = ans.comment || "";
  });
}

window.selectValOption = (qId, oIdx) => {
  validatorAnswers[qId].selectedIndex = oIdx;
  document.querySelectorAll(`#qcard-${qId} .val-opt`).forEach((btn) => {
    btn.classList.toggle("selected", parseInt(btn.dataset.oidx) === oIdx);
  });
};

window.selectValConfidence = (qId, lvl) => {
  validatorAnswers[qId].confidence = lvl;
  document.querySelectorAll(`#qcard-${qId} .val-conf-btn`).forEach((btn) => {
    btn.classList.toggle("selected", parseInt(btn.textContent) === lvl);
  });
};

window.updateValComment = (qId, val) => {
  validatorAnswers[qId].comment = val;
};

window.submitValidatorAnswers = async () => {
  const qIds = Object.keys(validatorAnswers);
  const unanswered = qIds.filter(
    (id) => validatorAnswers[id].selectedIndex === null,
  );
  if (unanswered.length > 0) {
    toast(`Please answer all questions before submitting.`, true);
    return;
  }
  const payload = qIds.map((id) => ({
    questionId: id,
    selectedIndex: validatorAnswers[id].selectedIndex,
    confidence: validatorAnswers[id].confidence,
    comment: validatorAnswers[id].comment,
  }));
  $("#val-submit-btn").disabled = true;
  $("#val-submit-btn").textContent = "Submitting...";

  try {
    const score = await api(`/api/validator/runs/${currentRunId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: payload }),
    });
    toast("Answers submitted!");
    renderValidatorResults(score);
  } catch (e) {
    toast(e.message, true);
    $("#val-submit-btn").disabled = false;
    $("#val-submit-btn").textContent = "Submit Answers";
  }
};

function renderValidatorResults(score) {
  $("#val-qa-container").innerHTML = "";
  $("#val-results").style.display = "block";
  $("#val-score").textContent = `${score.clarityScore}%`;
  $("#val-rating").textContent = score.rating;
  $("#val-rating").className = "v " + (score.clarityScore >= 75 ? "ok" : "err");
  $("#val-weak-count").textContent = score.weakAreas.length;

  if (score.weakAreas.length) {
    $("#val-weak-list").innerHTML =
      score.weakAreas
        .map(
          (w) =>
            `<span class="badge" style="color:var(--red);margin-right:6px">${esc(w.replace("_", " "))}</span>`,
        )
        .join("") +
      `<div style="margin-top:8px;font-size:12.5px" class="err">These categories scored below 60% accuracy, indicating requirement gaps.</div>`;
  } else {
    $("#val-weak-list").innerHTML =
      `<span class="badge new" style="color:var(--green)">None</span> <span class="muted" style="margin-left:6px">Strong requirement clarity across all categories.</span>`;
  }

  const results = score.questionResults || [];
  $("#val-details-list").innerHTML = results
    .map((q, idx) => {
      const isCorrect = q.isCorrect;
      return `
    <div class="val-qcard" style="border-left: 4px solid ${isCorrect ? "var(--green)" : "var(--red)"}">
      <div class="category">${esc(q.category.replace("_", " "))}</div>
      <div class="qtext">${idx + 1}. ${esc(q.question)}</div>
      <div style="font-size:12.5px;margin-bottom:6px">
        <b>Your Answer:</b> <span style="color:${isCorrect ? "var(--green)" : "var(--red)"}">${esc(q.selectedOption || "unanswered")}</span>
        ${isCorrect ? "" : `<br><b>Correct Answer:</b> <span style="color:var(--green)">${esc(q.correctOption)}</span>`}
      </div>
      ${q.comment ? `<div class="muted" style="background:var(--panel);padding:6px 10px;border-radius:6px;margin-top:6px"><b>Note:</b> ${esc(q.comment)}</div>` : ""}
    </div>`;
    })
    .join("");
}

$("#val-retake-btn").onclick = async () => {
  if (
    await uiConfirm(
      "Are you sure you want to retake the validator? This will generate completely fresh questions.",
      "Retake Validator",
    )
  ) {
    runValidator(true);
  }
};

