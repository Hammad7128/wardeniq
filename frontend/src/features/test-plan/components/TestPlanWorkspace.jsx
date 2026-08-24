/** TestPlanWorkspace for test-plan. */
export default function TestPlanWorkspace() {
  return (
    <div className="card" id="tp-workspace" style={{ display: "none" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 id="tp-feat-title">Test Plan</h2>
        <div style={{ display: "flex", gap: "6px" }}>
          <button className="go" id="tp-generate-btn">Generate Test Plan</button>
          <a className="ghost" id="tp-export-csv" style={{ display: "none", textDecoration: "none" }}>Export CSV</a>
          <a className="ghost" id="tp-export-pdf" style={{ display: "none", textDecoration: "none" }}>Export PDF</a>
        </div>
      </div>
      <div className="sub">Comprehensive feature-specific QA test plan, generated dynamically from requirements.</div>
      <div id="tp-progress" className="progress" style={{ display: "none" }}>
        <div className="pbar" id="tp-bar"></div>
      </div>
      <div id="tp-status" className="muted" style={{ marginBottom: "12px" }}></div>
      <div id="tp-content" className="muted" style={{ marginTop: "15px", background: "var(--panel2)", border: "1px solid var(--line)", borderRadius: "8px", padding: "16px", overflowY: "auto", maxHeight: "600px", fontFamily: "monospace", whiteSpace: "pre-wrap", lineHeight: "1.6", color: "var(--text)" }}></div>
    </div>
  );
}
