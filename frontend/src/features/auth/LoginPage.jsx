import { useState, useEffect } from "react";
import { api } from "../../lib/api";

export default function LoginPage({ onAuthenticated }) {
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState("login"); // "login" | "forgot-request" | "forgot-reset"
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [smtpSetup, setSmtpSetup] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // Forgot password state
  const [resetTarget, setResetTarget] = useState("admin");
  const [resetCode, setResetCode] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    api("/api/auth/smtp-status")
      .then((res) => {
        if (res) {
          setSmtpSetup(res.smtp_setup);
        }
      })
      .catch(() => {});
  }, []);

  const loginPassword = async () => {
    setErr("");
    setMsg("");
    if (!username.trim()) {
      setErr("Username is required.");
      return;
    }
    if (!password) {
      setErr("Password is required.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/auth/login-password", {
        method: "POST",
        body: { username: username.trim(), password },
      });
      onAuthenticated?.();
    } catch (e) {
      setErr(e.message || "Login failed.");
    } finally {
      setBusy(false);
    }
  };

  const sendCode = async () => {
    setErr("");
    setMsg("");
    if (!email.trim()) {
      setErr("Email is required.");
      return;
    }
    setBusy(true);
    try {
      const r = await api("/api/auth/request-otp", {
        method: "POST",
        body: { email: email.trim() },
      });
      setMsg(
        r?.dev_code
          ? `Dev mode (no SMTP): your code is ${r.dev_code}`
          : "Code sent. Check your inbox."
      );
      setStep(2);
    } catch (e) {
      setErr(e.message || "Could not send code.");
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    setErr("");
    setMsg("");
    if (!code.trim()) {
      setErr("Enter the 6-digit code.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/auth/verify-otp", {
        method: "POST",
        body: { email: email.trim(), code: code.trim() },
      });
      onAuthenticated?.();
    } catch (e) {
      setErr(e.message || "Verification failed.");
    } finally {
      setBusy(false);
    }
  };

  const requestPasswordReset = async () => {
    setErr("");
    setMsg("");
    if (!resetTarget.trim()) {
      setErr("Username or email is required.");
      return;
    }
    setBusy(true);
    try {
      const r = await api("/api/auth/request-password-reset", {
        method: "POST",
        body: { username_or_email: resetTarget.trim() },
      });
      if (r?.smtp_configured) {
        setMsg("Reset code sent. Check your email inbox.");
        setMode("forgot-reset");
      } else {
        setMsg("SMTP is not configured. Use your App Master Secret to reset.");
      }
    } catch (e) {
      setErr(e.message || "Could not request password reset.");
    } finally {
      setBusy(false);
    }
  };

  const performPasswordReset = async () => {
    setErr("");
    setMsg("");
    if (!resetCode.trim()) {
      setErr("Enter the 6-digit reset code.");
      return;
    }
    if (!newPassword) {
      setErr("Enter a new password.");
      return;
    }
    setBusy(true);
    try {
      const r = await api("/api/auth/reset-password", {
        method: "POST",
        body: {
          username_or_email: resetTarget.trim(),
          code: resetCode.trim(),
          new_password: newPassword,
        },
      });
      setMsg(r?.message || "Password reset successfully. You can now sign in.");
      setMode("login");
      setPassword("");
      setResetCode("");
      setNewPassword("");
    } catch (e) {
      setErr(e.message || "Password reset failed.");
    } finally {
      setBusy(false);
    }
  };

  const performMasterPasswordReset = async () => {
    setErr("");
    setMsg("");
    if (!appSecret.trim()) {
      setErr("App Master Secret (APP_SECRET) is required.");
      return;
    }
    if (!newPassword) {
      setErr("Enter a new password.");
      return;
    }
    setBusy(true);
    try {
      const r = await api("/api/auth/reset-password-master", {
        method: "POST",
        body: {
          username: resetTarget.trim() || "admin",
          app_secret: appSecret.trim(),
          new_password: newPassword,
        },
      });
      setMsg(r?.message || "Password reset successfully. You can now sign in.");
      setMode("login");
      setPassword("");
      setAppSecret("");
      setNewPassword("");
    } catch (e) {
      setErr(e.message || "Master secret password reset failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-bg">
      <div className="w-[360px] max-w-[92vw] rounded-2xl border border-line bg-panel p-6 shadow-2xl">
        <div className="mb-3 flex items-center gap-3 text-left">
          <svg
            width="42"
            height="42"
            viewBox="0 0 100 80"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="shrink-0"
          >
            <rect x="22" y="10" width="12" height="60" fill="#1c7ec2" />
            <rect x="44" y="10" width="12" height="60" fill="#1c7ec2" />
            <rect x="66" y="10" width="12" height="60" fill="#1c7ec2" />
            <path
              d="M 5,38 C 15,38 15,48 25,48 H 36 C 44,48 44,40 50,40 C 56,40 56,48 64,48 H 75 C 85,48 85,62 95,62"
              stroke="#1ce5b2"
              strokeWidth="5"
              fill="none"
              strokeLinecap="round"
            />
            <circle cx="5" cy="38" r="5" fill="#1ce5b2" />
            <circle cx="5" cy="38" r="2.2" fill="#141a24" />
            <circle cx="95" cy="62" r="5" fill="#1ce5b2" />
            <circle cx="95" cy="62" r="2.2" fill="#141a24" />
            <circle cx="50" cy="40" r="10" fill="#141a24" stroke="#1ce5b2" strokeWidth="5" />
          </svg>
          <div className="flex flex-col leading-tight">
            <span className="text-[26px] font-extrabold tracking-tight text-[#1c7ec2]">
              Warden<span className="text-[#1c7ec2]">IQ</span>
            </span>
            <span className="mt-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-[#1ce5b2]">
              Engineering Intelligence
            </span>
          </div>
        </div>
        <p className="mb-4 text-[12.5px] text-muted">
          {mode !== "login"
            ? "Reset your account password."
            : smtpSetup
            ? "Sign in with a one-time code sent to your email."
            : "Sign in with your admin credentials. (SMTP is not configured)"}
        </p>

        {mode === "login" && !smtpSetup && (
          <div>
            <label className="mb-1 block text-xs text-muted">Username / Email</label>
            <input
              type="text"
              placeholder="admin"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <div className="mt-3 flex items-center justify-between">
              <label className="text-xs text-muted">Password</label>
              <button
                type="button"
                onClick={() => {
                  setMode("forgot-request");
                  setErr("");
                  setMsg("");
                }}
                className="text-xs text-accent hover:underline"
              >
                Forgot password?
              </button>
            </div>
            <input
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loginPassword()}
              className="mt-1 w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={loginPassword}
              disabled={busy}
              className="mt-4 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </div>
        )}

        {mode === "login" && smtpSetup && step === 1 && (
          <div>
            <label className="mb-1 block text-xs text-muted">Email</label>
            <input
              type="email"
              placeholder="you@company.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendCode()}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={sendCode}
              disabled={busy}
              className="mt-3 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Sending…" : "Send code"}
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("forgot-request");
                setErr("");
                setMsg("");
              }}
              className="mt-2.5 w-full text-center text-xs text-accent hover:underline"
            >
              Reset local/admin password
            </button>
          </div>
        )}

        {mode === "login" && smtpSetup && step === 2 && (
          <div>
            <label className="mb-1 block text-xs text-muted">
              6-digit code sent to <b className="text-text">{email}</b>
            </label>
            <input
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && verify()}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-center text-lg tracking-[0.5em] text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={verify}
              disabled={busy}
              className="mt-3 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Verifying…" : "Verify & sign in"}
            </button>
            <button
              onClick={() => {
                setStep(1);
                setCode("");
                setErr("");
                setMsg("");
              }}
              className="mt-2 w-full border-none bg-transparent px-0 py-2 text-left text-xs text-accent2 hover:underline"
            >
              ← use a different email
            </button>
          </div>
        )}

        {mode === "forgot-request" && !smtpSetup && (
          <div className="text-left">
            <div className="mb-3 rounded-lg border border-line bg-panel2 p-3 text-xs text-muted leading-relaxed">
              <span className="font-semibold text-text">SMTP is not configured.</span> Reset your password directly by providing your deployment's <span className="font-mono text-accent">APP_SECRET</span>.
            </div>
            <label className="mb-1 block text-xs text-muted">Username</label>
            <input
              type="text"
              placeholder="admin"
              value={resetTarget}
              onChange={(e) => setResetTarget(e.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <label className="mt-3 mb-1 block text-xs text-muted">App Master Secret (APP_SECRET)</label>
            <input
              type="password"
              placeholder="Container APP_SECRET"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <label className="mt-3 mb-1 block text-xs text-muted">New Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && performMasterPasswordReset()}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={performMasterPasswordReset}
              disabled={busy}
              className="mt-4 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Resetting…" : "Reset Password"}
            </button>
            <button
              onClick={() => {
                setMode("login");
                setErr("");
                setMsg("");
              }}
              className="mt-2.5 w-full text-center text-xs text-muted hover:underline"
            >
              ← Back to Sign In
            </button>
          </div>
        )}

        {mode === "forgot-request" && smtpSetup && (
          <div className="text-left">
            <label className="mb-1 block text-xs text-muted">Username / Email</label>
            <input
              type="text"
              placeholder="you@company.com"
              value={resetTarget}
              onChange={(e) => setResetTarget(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && requestPasswordReset()}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={requestPasswordReset}
              disabled={busy}
              className="mt-3 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Sending reset code…" : "Email Reset Code"}
            </button>
            <button
              onClick={() => {
                setMode("login");
                setErr("");
                setMsg("");
              }}
              className="mt-2.5 w-full text-center text-xs text-muted hover:underline"
            >
              ← Back to Sign In
            </button>
          </div>
        )}

        {mode === "forgot-reset" && (
          <div>
            <label className="mb-1 block text-xs text-muted">6-digit Reset Code</label>
            <input
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              value={resetCode}
              onChange={(e) => setResetCode(e.target.value)}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-center text-lg tracking-[0.5em] text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <label className="mt-3 mb-1 block text-xs text-muted">New Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && performPasswordReset()}
              className="w-full rounded-md border border-line bg-panel2 px-3 py-2.5 text-sm text-text outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
            />
            <button
              onClick={performPasswordReset}
              disabled={busy}
              className="mt-4 w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-[#1a1205] transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Resetting…" : "Set New Password"}
            </button>
            <button
              onClick={() => {
                setMode("login");
                setErr("");
                setMsg("");
              }}
              className="mt-2.5 w-full text-center text-xs text-muted hover:underline"
            >
              ← Cancel & Sign In
            </button>
          </div>
        )}

        {msg && <div className="mt-2.5 text-xs text-green">{msg}</div>}
        {err && <div className="mt-2 min-h-[16px] text-xs text-red">{err}</div>}
      </div>
    </div>
  );
}
