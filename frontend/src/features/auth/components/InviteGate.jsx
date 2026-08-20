/**
 * InviteGate
 *
 * React-owned authentication markup. The existing backend/session behavior is
 * preserved by the auth compatibility controller while the old all-in-one
 * HTML shell is retired.
 */
export default function InviteGate() {
  return (
    <div id="invite-gate" hidden>
      <div className="box invite-box">
        <div className="invite-icon">
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 7l9 6 9-6" stroke="#1ce5b2" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"></path>
            <rect x="3" y="5" width="18" height="14" rx="2.5" stroke="#1ce5b2" strokeWidth="1.8"></rect>
          </svg>
        </div>
        <h2 style={{ margin: "6px 0 2px" }}>You&apos;ve been invited</h2>
        <p className="muted" id="invite-sub" style={{ marginTop: "0" }}>
          You&apos;ve been invited to join
          <b id="invite-workspace">WardenIQ</b>
          .
        </p>
        <div className="invite-meta" id="invite-meta"></div>
        <div className="invite-actions">
          <button className="go" id="invite-accept">Accept invitation</button>
          <button className="ghost" id="invite-decline">Decline</button>
        </div>
        <div className="err" id="invite-err"></div>
      </div>
    </div>
  );
}
