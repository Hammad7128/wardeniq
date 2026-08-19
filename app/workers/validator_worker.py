
from core.deps import current_llm
from core.state import store  # noqa: F401  (bare name-import is safe: store is
                               # mutated, never rebound)
import validator

from workers.registry import JOB_WORKERS


def _validator_worker(jid, params):
    run_id = params["run_id"]

    def update_fn(stage, progress=None):
        store.update_job_progress(jid, stage, progress)

    result = validator.generate_validator_run(
        store=store,
        llm=current_llm(),
        feature_id=params["feature_id"],
        run_id=run_id,
        progress_fn=update_fn,
    )
    store.merge_job_result(
        jid,
        run_id=run_id,
        question_count=len(result.get("questions") or []),
    )


JOB_WORKERS["validator"] = _validator_worker
