/** FeatureWorkspacePanel for features. */
export default function FeatureWorkspacePanel() {
  return (
    <div className="card stage-page" id="detail-card" hidden>
      <div className="feature-workspace-head">
        <div>
          <button className="ghost" id="d-close" style={{ marginBottom: "10px" }}>Back to features</button>
          <h2 id="d-name">Feature</h2>
        </div>
        <div className="workspace-actions">
          <span className="version-combo">
            <span className="version-chip" id="d-version-chip">Version 1</span>
            <button className="new-version-btn" id="d-newver" title="Create new version">+</button>
          </span>
          <select id="d-version" style={{ display: "none" }}></select>
          <button className="ghost" id="d-reuse-imports" type="button" title="Reuse imported sheet tests">↺ Reuse imported</button>
          <button id="d-export" className="export-btn">Export PDF</button>
          <button id="d-export-csv" className="export-btn" type="button">Export CSV</button>
          <button className="ghost" id="d-regen" style={{ display: "none" }}>Regenerate</button>
          <button className="ghost" id="d-jira" style={{ display: "none" }}>Sync to Jira</button>
          <button className="ghost" id="d-rename" style={{ display: "none" }}>Rename</button>
          <button className="danger" id="d-del" style={{ display: "none" }}>Delete feature</button>
        </div>
      </div>
      <div className="muted" id="d-meta"></div>
      <div id="d-match-key" className="muted" style={{ margin: "6px 0" }}></div>
      <div id="d-coverage"></div>
      <div id="d-overview"></div>
      <div id="d-verinfo"></div>
      <div id="d-genbanner"></div>
      <div className="case-bulk-toolbar" data-bulk-scope="feature">
        <div className="case-bulk-left">
          <span className="case-bulk-count" data-bulk-count="feature">0 selected</span>
        </div>
        <div className="case-bulk-actions">
          <button className="ghost bulk-pass" onClick={() => window.bulkSetCaseResult?.('passed')}>Pass selected</button>
          <button className="ghost bulk-fail" onClick={() => window.bulkSetCaseResult?.('failed')}>Fail selected</button>
          <button className="ghost" onClick={() => window.bulkSetCaseResult?.('untested')}>Clear status</button>
          <button className="ghost" onClick={() => window.bulkExportSelected?.('pdf')}>Export selected</button>
          <button className="testcase-delete" onClick={() => window.bulkDeleteSelected?.()}>Delete selected</button>
        </div>
      </div>
      <div id="d-cases"></div>
      <div className="case-bulk-toolbar bulk-floating" data-bulk-scope="feature-floating">
        <div className="case-bulk-left">
          <span className="badge" data-bulk-count="feature-floating">0</span>
          <span className="case-bulk-count">selected</span>
        </div>
        <div className="case-bulk-actions">
          <button className="ghost" onClick={() => window.bulkExportSelected?.('pdf')}>Export selected</button>
          <button className="testcase-delete" onClick={() => window.bulkDeleteSelected?.()}>Delete selected</button>
        </div>
      </div>
    </div>
  );
}
