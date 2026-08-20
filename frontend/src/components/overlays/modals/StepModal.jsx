/** Shared step-modal overlay. */
export default function StepModal() {
  return (
    <div className="modal" id="step-modal">
      <div className="box editor-box" style={{ maxWidth: "500px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 id="step-modal-heading" style={{ margin: "0", fontSize: "16px" }}>Create Step</h2>
          <button className="ghost" id="step-modal-close" type="button" style={{ padding: "4px 8px", fontSize: "16px" }}>×</button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <label>Step Type / Prefix</label>
            <select id="step-modal-prefix" style={{ width: "100%" }}>
              <option value="Given">Given</option>
              <option value="When">When</option>
              <option value="Then">Then</option>
              <option value="And">And</option>
              <option value="But">But</option>
              <option value="">None / Custom</option>
            </select>
          </div>
          <div>
            <label>Action / Description</label>
            <textarea id="step-modal-action" placeholder="e.g. user is on login page" style={{ width: "100%", height: "70px", fontFamily: "inherit", fontSize: "13px", padding: "8px" }} required></textarea>
          </div>
          <div>
            <label>Expected Result</label>
            <textarea id="step-modal-expected" placeholder="e.g. login form is displayed" style={{ width: "100%", height: "70px", fontFamily: "inherit", fontSize: "13px", padding: "8px" }}></textarea>
          </div>
          <div id="step-modal-warn" style={{ fontSize: "12px", color: "var(--amber)", marginTop: "4px", display: "none" }}></div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
            <button className="ghost" id="step-modal-cancel" type="button">Cancel</button>
            <button className="go" id="step-modal-save" type="button">Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}
