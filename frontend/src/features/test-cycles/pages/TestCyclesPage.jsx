import CreateTestCyclePanel from "../components/CreateTestCyclePanel.jsx";
import CycleTemplatesPanel from "../components/CycleTemplatesPanel.jsx";
import TestCyclesListPanel from "../components/TestCyclesListPanel.jsx";
import TestCycleDetailPanel from "../components/TestCycleDetailPanel.jsx";

export default function TestCyclesPage() {
  return (
    <section id="view-testcycles" className="view" hidden>
      <CreateTestCyclePanel />
      <CycleTemplatesPanel />
      <TestCyclesListPanel />
      <TestCycleDetailPanel />
    </section>
  );
}
