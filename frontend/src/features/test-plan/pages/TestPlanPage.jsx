import TestPlanHeader from "../components/TestPlanHeader.jsx";
import TestPlanEmptyState from "../components/TestPlanEmptyState.jsx";
import TestPlanWorkspace from "../components/TestPlanWorkspace.jsx";

export default function TestPlanPage() {
  return (
    <section id="view-testplan" className="view" hidden>
      <TestPlanHeader />
      <TestPlanEmptyState />
      <TestPlanWorkspace />
    </section>
  );
}
