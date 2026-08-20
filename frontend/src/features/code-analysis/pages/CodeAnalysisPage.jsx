/**
 * CodeAnalysisPage
 *
 * Structural React port of the original static screen markup.
 * Data loading and mutation behavior is currently supplied by the domain
 * compatibility controllers under src/compat/runtime/controllers.
 * Keeping the DOM contract here lets the UI be migrated screen-by-screen
 * without a single monolithic HTML template.
 */
export default function CodeAnalysisPage() {
  return (
    <section id="view-cycles" className="view" hidden>
      <div className="mindmap-shell">
        <div className="mindmap-hero">
          <div className="mindmap-toolbar">
            <div>
              <h2>Change impact analysis</h2>
              <div className="sub">
                Review recent implementation changes, map them to affected test
                cases, and turn the result into a release regression cycle. Pick
                any of the project&apos;s repos below to include in the
                analysis.
              </div>
              <div className="view-explainer">
                Answers
                <b>“which test cases do recent commits touch?”</b>— a
                change-driven view. To see whether the codebase actually
                implements each case, use the
                <b>Implementation coverage map</b>.
              </div>
            </div>
            <div className="mindmap-hero-actions">
              <button className="ghost mindmap-refresh-btn" id="cyc-refresh">
                <span className="icon">↻</span>
                <span>Refresh</span>
              </button>
            </div>
          </div>
          <div className="mindmap-controls">
            <div className="mindmap-control-project">
              <label>Project</label>
              <select id="cyc-proj" style={{ height: "38px" }}></select>
            </div>
            <div style={{ flex: "0 0 140px" }}>
              <label>Lookback (days)</label>
              <input
                id="cyc-days"
                type="number"
                defaultValue="14"
                min="1"
                max="180"
                style={{ height: "38px" }}
              />
            </div>
            <button className="go mindmap-primary-btn" id="cyc-analyze">
              Analyze changes
            </button>
          </div>
          <label style={{ marginTop: "8px" }}>
            Repos &amp; branches
            <span className="muted" style={{ fontWeight: "400" }}>
              — uncheck any to exclude; set a branch per repo (blank = its
              default). Infra repos start unchecked — tick them to include.
            </span>
          </label>
          <div
            id="cyc-repos"
            className="mindmap-panel"
            style={{ display: "flex", flexDirection: "column", gap: "8px" }}
          ></div>
          <button
            className="ghost"
            id="cyc-add-git"
            style={{
              marginTop: "8px",
              padding: "5px 12px",
              alignSelf: "flex-start",
            }}
          >
            + Add a repo from GitHub
          </button>
          <div
            className="muted"
            id="cyc-status"
            style={{ marginTop: "8px" }}
          ></div>
        </div>
        <div id="cyc-impacted"></div>
        <div
          className="mindmap-summary-card cycles-create-card"
          id="cyc-create"
          style={{ display: "none" }}
        >
          <div className="mindmap-summary-head">
            <h2>Create a test cycle</h2>
            <div className="mindmap-chip-row">
              <span className="badge">selected impacted cases</span>
            </div>
          </div>
          <div className="sub">
            Pick the impacted cases you want to retest, name the cycle, and save
            it for execution.
          </div>
          <div className="row" style={{ marginTop: "12px" }}>
            <input
              id="cyc-name"
              placeholder="Cycle name (for example: Sprint 12 regression)"
            />
            <button className="go" id="cyc-make" style={{ flex: "0 0 auto" }}>
              Create cycle
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
