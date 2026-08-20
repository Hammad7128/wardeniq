/**
 * UsagePage
 *
 * Structural React port of the original static screen markup.
 * Data loading and mutation behavior is currently supplied by the domain
 * compatibility controllers under src/compat/runtime/controllers.
 * Keeping the DOM contract here lets the UI be migrated screen-by-screen
 * without a single monolithic HTML template.
 */
export default function UsagePage() {
  return (
    <section id="view-usage" className="view" hidden>
      <div className="mindmap-shell">
        <div className="mindmap-hero usage-hero">
          <div className="mindmap-toolbar">
            <div>
              <h2>LLM usage &amp; cost</h2>
              <div className="sub">Monitor and control AI spend. Every process — test-case generation, PR coverage, commit &amp; Mind-Map analysis, and ingestion — reports the tokens it consumed and which model it used. This dashboard rolls that up into total tokens, spend by model, spend by project, and a per-process breakdown so you can see exactly where cost comes from.</div>
            </div>
            <div className="mindmap-hero-actions">
              <button className="ghost mindmap-refresh-btn" id="usage-refresh">
                <span className="icon">↻</span>
                <span>Refresh</span>
              </button>
            </div>
          </div>
          <div id="usage-totals" className="usage-stats"></div>
          <div className="usage-formula">Cost = (input tokens ÷ 1,000,000 × input price) + (output tokens ÷ 1,000,000 × output price), per model, summed per process. Prices come from the per-model table below (editable); local Ollama models are free. Figures can still differ slightly from a provider console when prompt caching or batch discounts apply.</div>
        </div>
        <div className="card">
          <h3 style={{ margin: "0 0 8px", fontSize: "14px" }}>Recent processes</h3>
          <input id="usage-recent-search" className="usage-search" placeholder="Search process, project, or feature\u2026" />
          <div id="usage-recent"></div>
        </div>
        <details className="card usage-collapse" open>
          <summary>
            <span className="usage-collapse-title">By model</span>
            <span className="usage-collapse-hint muted">tokens &amp; cost per model</span>
          </summary>
          <div className="usage-filter-row">
            <label className="muted">Model</label>
            <select id="usage-model-filter" className="usage-select">
              <option value="">All models</option>
            </select>
          </div>
          <div id="usage-by-model"></div>
        </details>
        <details className="card usage-collapse">
          <summary>
            <span className="usage-collapse-title">By project</span>
            <span className="usage-collapse-hint muted">tokens &amp; cost per project</span>
          </summary>
          <div className="usage-filter-row">
            <label className="muted">Project</label>
            <select id="usage-project-filter" className="usage-select">
              <option value="">All projects</option>
            </select>
          </div>
          <div id="usage-by-project"></div>
        </details>
      </div>
    </section>
  );
}
