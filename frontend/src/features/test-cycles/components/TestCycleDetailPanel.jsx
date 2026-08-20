/** TestCycleDetailPanel for test-cycles. */
export default function TestCycleDetailPanel() {
  return (
    <div className="card" id="cyc-detail-card" style={{ display: "none" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 id="cyc-d-name" style={{ margin: "0" }}>Cycle</h2>
        <div style={{ display: "flex", gap: "6px" }}>
          <button className="ghost" id="cyc-d-rename">Rename</button>
          <button className="danger" id="cyc-d-del">Delete cycle</button>
          <button className="ghost" id="cyc-d-close">Close</button>
        </div>
      </div>
      <div id="cyc-d-items"></div>
    </div>
  );
}
