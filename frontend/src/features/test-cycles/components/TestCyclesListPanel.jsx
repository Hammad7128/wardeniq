/** TestCyclesListPanel for test-cycles. */
export default function TestCyclesListPanel() {
  return (
    <div className="card">
      <h2>Test cycles</h2>
      <div className="sub">Saved release regression cycles for the selected project.</div>
      <div id="cyc-list"></div>
    </div>
  );
}
