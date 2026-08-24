import ProjectListPanel from "../components/ProjectListPanel.jsx";
import ProjectDetailPanel from "../components/ProjectDetailPanel.jsx";

export default function ProjectsPage() {
  return (
    <section id="view-projects" className="view" hidden>
      <ProjectListPanel />
      <ProjectDetailPanel />
    </section>
  );
}
