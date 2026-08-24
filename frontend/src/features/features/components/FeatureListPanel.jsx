/** FeatureListPanel for features. */
export default function FeatureListPanel() {
  return (
    <div id="feature-list-page" className="stage-page">
      <div className="page-toolbar">
        <div>
          <button className="ghost" id="features-back-project" style={{ marginBottom: "12px" }}>Back to projects</button>
          <h2 id="features-page-title">Features</h2>
          <div className="sub" id="features-project-context"></div>
        </div>
        <button className="go" id="feature-new-btn">+ New feature</button>
      </div>
      <div id="feat-list" className="entity-grid"></div>
    </div>
  );
}
