import FeatureListPanel from "../components/FeatureListPanel.jsx";
import FeatureCreatePanel from "../components/FeatureCreatePanel.jsx";
import FeatureWorkspacePanel from "../components/FeatureWorkspacePanel.jsx";

export default function FeaturesPage() {
  return (
    <section id="view-features" className="view" hidden>
      <FeatureListPanel />
      <FeatureCreatePanel />
      <FeatureWorkspacePanel />
    </section>
  );
}
