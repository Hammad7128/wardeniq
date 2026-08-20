import GapHeader from "../components/GapHeader.jsx";
import GapEmptyState from "../components/GapEmptyState.jsx";
import GapWorkspace from "../components/GapWorkspace.jsx";

export default function GapAnalysisPage() {
  return (
    <section id="view-gap" className="view" hidden>
      <GapHeader />
      <GapEmptyState />
      <GapWorkspace />
    </section>
  );
}
