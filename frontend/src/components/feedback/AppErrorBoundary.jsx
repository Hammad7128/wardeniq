import React from "react";

export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("WardenIQ frontend error", error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
        <div className="w-full max-w-lg rounded-2xl border border-rose-400/20 bg-slate-900 p-6 shadow-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-rose-300">Application error</p>
          <h1 className="mt-2 text-xl font-semibold">WardenIQ could not render this screen.</h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            Refresh the page. If the issue continues, check the browser console and backend logs.
          </p>
          <button
            className="mt-5 rounded-lg bg-sky-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sky-400"
            onClick={() => window.location.reload()}
          >
            Reload application
          </button>
        </div>
      </div>
    );
  }
}
