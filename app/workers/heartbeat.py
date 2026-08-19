
import threading
from contextlib import contextmanager

from core.state import store

# Comfortably under BOTH watchdogs above (120s frontend, 600s backend default)
# so neither ever mistakes a live worker for a dead one.
HEARTBEAT_SECONDS = 45


@contextmanager
def heartbeat(jid, message=None, interval=HEARTBEAT_SECONDS):
    """Re-touch `updated_at` on job `jid` every `interval` seconds for as long
    as the wrapped block runs. Stops as soon as the block exits (success,
    exception, or the job having already reached a final status).

    `message` controls the stage caption written on each tick:
      * None (default) — reuse whatever stage is already on the job, so the
        caption stays exactly what the worker itself last set; only the
        timestamp refreshes.
      * a string — a fixed caption for the whole block.
      * a zero-arg callable — re-invoked on every tick, for a caption that
        changes mid-block (e.g. "embedding {repo} — {path}").
    """
    stop = threading.Event()

    def _caption(current_stage):
        if callable(message):
            try:
                return message() or current_stage or "working…"
            except Exception:  # noqa: BLE001
                return current_stage or "working…"
        return message or current_stage or "working…"

    def _loop():
        while not stop.wait(interval):
            try:
                j = store.get_job(jid)
                if not j or j.get("status") != "running":
                    return   # job already finished/failed elsewhere — stop quietly
                store.update_job(jid, stage=_caption(j.get("stage")))
            except Exception:  # noqa: BLE001
                pass   # never let heartbeat bookkeeping crash the actual worker

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)
