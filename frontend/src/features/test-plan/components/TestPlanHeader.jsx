/** TestPlanHeader for test-plan. */
export default function TestPlanHeader() {
  return (
    <div style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
      <button className="ghost feature-workspace-back">Feature workspace</button>
      <button className="ghost feature-workspace-cases">Test Cases</button>
    </div>
  );
}
