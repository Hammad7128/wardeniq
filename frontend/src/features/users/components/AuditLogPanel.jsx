/** AuditLogPanel for users. */
export default function AuditLogPanel() {
  return (
    <div className="card">
      <h2>Audit log</h2>
      <div className="sub">Recent security-relevant actions (invites, role changes, deletes, settings, denied access).</div>
      <div id="audit-list">
        <span className="muted">Loading…</span>
      </div>
    </div>
  );
}
