/**
 * StepLibraryPage
 *
 * Structural React port of the original static screen markup.
 * Data loading and mutation behavior is currently supplied by the domain
 * compatibility controllers under src/compat/runtime/controllers.
 * Keeping the DOM contract here lets the UI be migrated screen-by-screen
 * without a single monolithic HTML template.
 */
export default function StepLibraryPage() {
  return (
    <section id="view-steps" className="view" hidden>
      <div style={{ display: "flex", gap: "18px", alignItems: "stretch", minHeight: "calc(100vh - 140px)" }}>
        {/* Left Main Step Management Pane */}
        <div style={{ flex: "1", minWidth: "0", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card" style={{ marginBottom: "0" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h2 style={{ margin: "0", display: "inline-flex", alignItems: "center", gap: "8px" }}>
                  Step library
                  <span className="badge" id="s-count" style={{ fontSize: "12px", background: "rgba(255,255,255,0.06)", color: "var(--text)" }}></span>
                </h2>
                <div className="sub" style={{ marginTop: "4px" }}>Shared building blocks for test cases — write a step once and reuse it everywhere instead of duplicating it. Near-duplicate steps are auto-merged, and editing a step here updates every test case that references it.</div>
              </div>
              <button className="go" id="s-new" type="button" style={{ margin: "0" }}>+ New step</button>
            </div>
            {/* Search, Filter & Sort Bar */}
            <div style={{ display: "flex", gap: "10px", marginTop: "16px", flexWrap: "wrap", alignItems: "center" }}>
              <input type="text" id="s-search" placeholder="Search steps by action or expected result..." style={{ flex: "1", minWidth: "240px", height: "38px", padding: "8px 12px", background: "#0d1728", border: "1px solid #1E2A40", borderRadius: "6px", color: "#e2e8f0", fontSize: "13.5px" }} />
              <select id="s-filter-type" style={{ width: "140px", height: "38px", padding: "0 8px", background: "#0d1728", border: "1px solid #1E2A40", borderRadius: "6px", color: "#e2e8f0", fontSize: "13.5px" }}>
                <option value="">All Types</option>
                <option value="Given">Given</option>
                <option value="When">When</option>
                <option value="Then">Then</option>
                <option value="And">And/But</option>
                <option value="Other">Other / Action</option>
              </select>
              <select id="s-filter-usage" style={{ width: "140px", height: "38px", padding: "0 8px", background: "#0d1728", border: "1px solid #1E2A40", borderRadius: "6px", color: "#e2e8f0", fontSize: "13.5px" }}>
                <option value="">All Usages</option>
                <option value="used">Used steps</option>
                <option value="unused">Unused steps</option>
              </select>
            </div>
          </div>
          {/* Steps list card */}
          <div className="card" style={{ flex: "1", padding: "0", overflow: "hidden", border: "1px solid #1E2A40", background: "#07111f", borderRadius: "10px", display: "flex", flexDirection: "column" }}>
            <div style={{ flex: "1", overflowY: "auto", maxHeight: "650px" }}>
              <div id="s-list-body">
                {/* Loaded dynamically */}
              </div>
            </div>
          </div>
        </div>
        {/* Right Collapsible Detail/Usage Drawer (1/3 width) */}
        <div id="s-detail-pane" style={{ width: "360px", display: "none", flexDirection: "column", gap: "16px", background: "var(--panel)", border: "1px solid var(--line)", borderRadius: "10px", padding: "18px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1E2A40", paddingBottom: "12px" }}>
            <h3 style={{ margin: "0", fontSize: "14px", color: "#e2e8f0" }}>Step Detail</h3>
            <button className="ghost" id="s-detail-close" type="button" style={{ padding: "2px 6px" }}>Close</button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div>
              <span className="muted" style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Type</span>
              <div id="s-detail-type" style={{ marginTop: "4px" }}></div>
            </div>
            <div>
              <span className="muted" style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Action / Description</span>
              <div id="s-detail-action" style={{ marginTop: "4px", fontSize: "13.5px", color: "#e2e8f0", fontWeight: "500", lineHeight: "1.4", wordBreak: "break-word" }}></div>
            </div>
            <div>
              <span className="muted" style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Expected Result</span>
              <div id="s-detail-expected" style={{ marginTop: "4px", fontSize: "13px", color: "#cbd5e1", lineHeight: "1.4", wordBreak: "break-word" }}></div>
            </div>
            <div style={{ borderTop: "1px solid #1E2A40", paddingTop: "12px" }}>
              <span id="s-detail-cases-title" style={{ fontSize: "11.5px", fontWeight: "600", color: "#94a3b8", display: "flex", alignItems: "center", gap: "6px" }}>Used in Cases (0)</span>
              <div id="s-detail-cases-list" style={{ marginTop: "8px", maxHeight: "300px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
                {/* Mapped cases loaded dynamically */}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
