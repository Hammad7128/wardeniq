import ValidatorHeader from "../components/ValidatorHeader.jsx";
import ValidatorEmptyState from "../components/ValidatorEmptyState.jsx";
import ValidatorWorkspace from "../components/ValidatorWorkspace.jsx";

export default function ValidatorPage() {
  return (
    <section id="view-validator" className="view" hidden>
      <ValidatorHeader />
      <ValidatorEmptyState />
      <ValidatorWorkspace />
    </section>
  );
}
