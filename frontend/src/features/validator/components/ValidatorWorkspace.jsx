/** ValidatorWorkspace for validator. */
export default function ValidatorWorkspace() {
  return (
    <div className="card" id="val-workspace" style={{ display: "none" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 id="val-feat-title">MCQ Validator</h2>
        <div style={{ display: "flex", gap: "6px" }}>
          <button className="go" id="val-generate-btn">Generate Validator</button>
          <button className="ghost" id="val-retake-btn">↻ Retake Validator</button>
        </div>
      </div>
      <div className="sub">Resolve requirement ambiguity, validate business intent, and detect gaps before QA begins.</div>
      <div id="val-progress" className="progress" style={{ display: "none" }}>
        <div className="pbar" id="val-bar"></div>
      </div>
      <div className="job-log" id="val-log"></div>
      <div id="val-status" className="muted" style={{ marginBottom: "12px" }}></div>
      <div id="val-qa-container"></div>
      <div id="val-results" style={{ display: "none" }}>
        <div className="kpis" style={{ marginBottom: "20px" }}>
          <div className="kpi">
            <div className="v accent" id="val-score">-</div>
            <div className="l">Clarity Score</div>
          </div>
          <div className="kpi">
            <div className="v" id="val-rating">-</div>
            <div className="l">Rating</div>
          </div>
          <div className="kpi">
            <div className="v" id="val-weak-count">-</div>
            <div className="l">Weak Categories</div>
          </div>
        </div>
        <h3 style={{ marginTop: "20px", fontSize: "14px", color: "var(--accent)", borderBottom: "1px solid var(--line)", paddingBottom: "6px" }}>Weak Requirement Areas</h3>
        <div id="val-weak-list" className="muted" style={{ margin: "10px 0" }}></div>
        <h3 style={{ marginTop: "20px", fontSize: "14px", color: "var(--accent)", borderBottom: "1px solid var(--line)", paddingBottom: "6px" }}>Detailed Question Results</h3>
        <div id="val-details-list" style={{ marginTop: "10px" }}></div>
      </div>
    </div>
  );
}
