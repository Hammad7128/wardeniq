/** Shared vmodal overlay. */
export default function ValidatorModal() {
  return (
    <div className="modal" id="vmodal">
      <div className="box" style={{ maxWidth: "540px" }}>
        <h2 style={{ margin: "0 0 4px", fontSize: "16px" }}>Upload new version</h2>
        <div className="muted" id="vm-feat"></div>
        <label>Modified documents (multiple)</label>
        <input type="file" id="vm-file" multiple accept=".pdf,.docx,.md,.txt,.markdown" />
        <div className="muted" style={{ fontSize: "11px", marginTop: "4px" }}>Links inside PDFs (and their sub-links) are fetched automatically — public web only.</div>
        <label>…and/or paste updated requirement text</label>
        <textarea id="vm-text" style={{ minHeight: "90px" }}></textarea>
        <label style={{ marginTop: "12px" }}>
          Confluence page links
          <span className="muted" style={{ fontWeight: "400" }}>(optional · one per line · child pages included)</span>
        </label>
        <textarea id="vm-confluence" rows="2" placeholder="https://your-org.atlassian.net/wiki/spaces/\u2026/pages/123456/\u2026"></textarea>
        <label style={{ marginTop: "10px" }}>
          Figma design links
          <span className="muted" style={{ fontWeight: "400" }}>(optional · one per line · needs a Figma token in Configuration)</span>
        </label>
        <textarea id="vm-figma" rows="2" placeholder="https://www.figma.com/file/<key>/\u2026"></textarea>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "12px" }}>
          <input type="checkbox" id="vm-replace" style={{ width: "auto" }} />
          <label style={{ margin: "0" }}>Override: replace the current version instead of bumping</label>
        </div>
        <div className="warn" style={{ marginTop: "6px" }}>New version → the LLM keeps still-valid cases, retires obsolete ones, and adds new ones (history preserved). Replace → regenerates this version from scratch.</div>
        <div style={{ marginTop: "14px", display: "flex", gap: "8px" }}>
          <button className="go" id="vm-go">Create version</button>
          <button className="ghost" id="vm-cancel">Cancel</button>
        </div>
        <div id="vm-msg" className="muted" style={{ marginTop: "8px" }}></div>
      </div>
    </div>
  );
}
