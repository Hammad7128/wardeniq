export default function Header() {
  return (
    <header className="sticky top-0  flex h-[72px] w-full items-center justify-between border-b border-slate-800/80 bg-[#0B111B]/95 px-7 backdrop-blur-xl">
      {/* Left side */}
      <div className="flex min-w-0 items-center gap-4">
        <div className="min-w-0">
          <span className="mb-0.5 block text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-600">
            Workspace
          </span>

          <h1
            id="view-title"
            className="truncate text-[20px] font-semibold tracking-[-0.02em] text-slate-100"
          >
            Dashboard
          </h1>
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Environment / AI status */}
        <div
          id="status"
          className="flex min-h-[36px] items-center rounded-xl border border-slate-800 bg-slate-900/60 px-3.5"
        >
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-30" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>

            <span className="muted">loading…</span>
          </div>
        </div>

        {/* Separator */}
        <div className="mx-1 h-8 w-px bg-slate-800" />

        {/* User controls */}
        <div
          className="usermenu items-center gap-3"
          id="usermenu"
          hidden
        >
          {/* User information */}
          <div className="user-id flex items-center gap-3">
            {/* Avatar */}
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-cyan-500/15 bg-gradient-to-br from-cyan-500/15 to-blue-500/10">
              <svg
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-cyan-400"
              >
                <path d="M20 21a8 8 0 0 0-16 0" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>

            {/* Name / role */}
            <div className="flex min-w-0 flex-col">
              <span
                id="user-email"
                className="user-email max-w-[160px] truncate text-[13px] font-medium leading-5 text-slate-200"
              />

              <span
                id="user-role"
                className="rolebadge viewer mt-0.5 w-fit text-[10px]"
              />
            </div>
          </div>

          {/* Change Password */}
          <button
            type="button"
            className="change-pw-btn group flex h-9 items-center gap-2 rounded-lg border border-transparent px-3 text-xs font-medium text-slate-400 transition-all duration-200 hover:border-slate-700 hover:bg-slate-800/70 hover:text-slate-100"
            id="change-pw-btn"
            title="Change your local admin password"
            hidden
          >
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="transition-colors group-hover:text-cyan-400"
            >
              <rect x="5" y="11" width="14" height="9" rx="2" />
              <path d="M8 11V8a4 4 0 0 1 8 0v3" />
            </svg>

            <span>Change password</span>
          </button>

          {/* Sign Out */}
          <button
            type="button"
            className="signout-btn group flex h-9 items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-900/70 px-3.5 text-xs font-semibold text-slate-300 transition-all duration-200 hover:border-red-500/30 hover:bg-red-500/10 hover:text-red-300"
            id="logout-btn"
            title="Sign out"
          >
            <svg
              viewBox="0 0 24 24"
              width="15"
              height="15"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="transition-transform duration-200 group-hover:translate-x-0.5"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <path d="m16 17 5-5-5-5" />
              <path d="M21 12H9" />
            </svg>

            <span>Sign out</span>
          </button>
        </div>
      </div>
    </header>
  );
}