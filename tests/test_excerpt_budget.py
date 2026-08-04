"""Tests for the Mind Map code-excerpt budget.

Why this file exists: a fixed 900-character per-chunk cap silently truncated whole
function bodies to ~27%, and the reviewer then reported real, implemented endpoints as
"not present in the provided code excerpts". Meanwhile a fixed 16,000-character total
pushed the Ollama prompt ~2,000 tokens past its 8k context, so the prompt was being
truncated a second time. Both are budget bugs, and both are load-bearing for accuracy.
"""
import coverage as cov


class _FakeLLM:
    def __init__(self, provider):
        self.provider = provider


def _chunk(path, size, repo="r"):
    return {"repo": repo, "path": path, "text": "X" * size}


class TestExcerptTotalChars:
    def test_ollama_budget_leaves_room_for_prompt_and_reply(self, monkeypatch):
        monkeypatch.delenv("MINDMAP_EXCERPT_TOTAL_CHARS", raising=False)
        monkeypatch.setenv("OLLAMA_MAX_NUM_CTX", "8192")
        total = cov.excerpt_total_chars(_FakeLLM("ollama"))
        # Whole prompt + reserved reply must fit inside the model's context.
        demand_tokens = ((total + cov._NON_CODE_PROMPT_CHARS) / cov._CHARS_PER_TOKEN
                         + cov.REVIEW_MAX_TOKENS)
        assert demand_tokens <= 8192, f"budget overflows context: {demand_tokens} tokens"

    def test_raising_the_ollama_context_widens_the_code_window(self, monkeypatch):
        monkeypatch.delenv("MINDMAP_EXCERPT_TOTAL_CHARS", raising=False)
        monkeypatch.setenv("OLLAMA_MAX_NUM_CTX", "8192")
        small = cov.excerpt_total_chars(_FakeLLM("ollama"))
        monkeypatch.setenv("OLLAMA_MAX_NUM_CTX", "32768")
        big = cov.excerpt_total_chars(_FakeLLM("ollama"))
        assert big > small * 2

    def test_hosted_provider_gets_a_much_larger_window(self, monkeypatch):
        monkeypatch.delenv("MINDMAP_EXCERPT_TOTAL_CHARS", raising=False)
        monkeypatch.setenv("OLLAMA_MAX_NUM_CTX", "8192")
        assert (cov.excerpt_total_chars(_FakeLLM("openai"))
                > cov.excerpt_total_chars(_FakeLLM("ollama")))

    def test_explicit_override_wins(self, monkeypatch):
        monkeypatch.setenv("MINDMAP_EXCERPT_TOTAL_CHARS", "12345")
        assert cov.excerpt_total_chars(_FakeLLM("openai")) == 12345

    def test_no_llm_defaults_to_the_conservative_local_budget(self, monkeypatch):
        monkeypatch.delenv("MINDMAP_EXCERPT_TOTAL_CHARS", raising=False)
        monkeypatch.setenv("OLLAMA_MAX_NUM_CTX", "8192")
        assert cov.excerpt_total_chars(None) == cov.excerpt_total_chars(_FakeLLM("ollama"))


class TestCodeExcerptBlock:
    def test_real_controller_body_survives_intact(self):
        """Regression for the verified false negative.

        `sendOtp` in the reviewed repo is 3,305 characters. Under the old 900-char cap the
        reviewer saw 27% of it and called the endpoint uncovered, though the route exists
        and is fully implemented. It must now arrive whole and unmarked.
        """
        body = "export async function sendOtp(req, res) {" + ("y" * 3260) + "}"
        assert len(body) > 3300
        out = cov._code_excerpt_block([_chunk("controllers/auth.controller.ts", 0)][:0]
                                      + [{"repo": "r", "path": "controllers/auth.controller.ts",
                                          "text": body}])
        assert "TRUNCATED" not in out
        assert body in out

    def test_oversized_chunk_is_marked_not_silently_cut(self):
        import re
        out = cov._code_excerpt_block([_chunk("a.ts", 50_000)], max_total=5000, max_per=1000)
        assert "TRUNCATED" in out
        # The stated hidden count must reconcile with what was actually shown, so the
        # model can reason about the size of the gap rather than guess.
        hidden = int(re.search(r"TRUNCATED — (\d+) more characters", out).group(1))
        shown = len(re.search(r"a\.ts\n(X*)", out).group(1))
        assert shown + hidden == 50_000

    def test_never_exceeds_the_total_budget(self):
        chunks = [_chunk(f"f{i}.ts", 5000) for i in range(20)]
        out = cov._code_excerpt_block(chunks, max_total=9000, max_per=4000)
        assert len(out) <= 9000, f"budget blown: {len(out)}"

    def test_packs_several_complete_chunks_when_they_fit(self):
        chunks = [_chunk(f"f{i}.ts", 1000) for i in range(4)]
        out = cov._code_excerpt_block(chunks, max_total=20000, max_per=4000)
        assert "TRUNCATED" not in out
        for i in range(4):
            assert f"f{i}.ts" in out

    def test_stops_cleanly_rather_than_emitting_a_useless_sliver(self):
        chunks = [_chunk("big.ts", 4000), _chunk("second.ts", 4000)]
        out = cov._code_excerpt_block(chunks, max_total=4200, max_per=4000)
        assert "big.ts" in out
        assert "second.ts" not in out          # no 100-char fragment of the next file
        assert len(out) <= 4200

    def test_headers_identify_the_file_for_citation(self):
        out = cov._code_excerpt_block([_chunk("pkg/mod.ts", 100, repo="org/repo")])
        assert "// FILE org/repo:pkg/mod.ts" in out

    def test_empty_and_malformed_input(self):
        assert cov._code_excerpt_block([]) == ""
        # a chunk with no text still names its file, and emits no dangling blank body
        assert cov._code_excerpt_block([{"repo": "r", "path": "a.ts"}]) == "// FILE r:a.ts"

    def test_marker_is_paid_for_out_of_the_budget(self):
        # The marker is part of the emitted block; if it isn't reserved, every truncated
        # chunk silently overruns max_total (it did, by ~70 chars per chunk).
        for total in (1000, 2500, 4096, 9000):
            out = cov._code_excerpt_block([_chunk("a.ts", 50_000)], max_total=total,
                                          max_per=total)
            assert len(out) <= total, f"overran {total}: {len(out)}"

    def test_chunk_ceiling_is_the_configured_guard_not_a_hidden_twenty(self):
        # A bare [:20] silently discarded whatever retrieval selected past the 20th chunk,
        # so widening retrieval had no effect. The ceiling must be the configured value.
        chunks = [_chunk(f"f{i}.ts", 10) for i in range(cov.EXCERPT_MAX_CHUNKS + 15)]
        out = cov._code_excerpt_block(chunks, max_total=1_000_000, max_per=4000)
        assert out.count("// FILE") == cov.EXCERPT_MAX_CHUNKS
        assert cov.EXCERPT_MAX_CHUNKS > 20

    def test_character_budget_binds_before_the_chunk_ceiling(self):
        # The budget should be what actually limits the prompt, not an arbitrary count.
        chunks = [_chunk(f"f{i}.ts", 2000) for i in range(cov.EXCERPT_MAX_CHUNKS)]
        out = cov._code_excerpt_block(chunks, max_total=8000, max_per=4000)
        assert len(out) <= 8000
        assert out.count("// FILE") < cov.EXCERPT_MAX_CHUNKS


class TestPromptTellsModelHowToReadTruncation:
    def test_prompt_forbids_inferring_absence_from_truncation(self):
        p = cov._codereview_prompt("F", "req", "// FILE r:a.ts\ncode // ...TRUNCATED", [])
        assert "TRUNCATION" in p
        assert "never as proof of absence" in p
        assert "'partial'" in p

    def test_prompt_still_forbids_crediting_test_code(self):
        p = cov._codereview_prompt("F", "req", "code", [])
        assert "test could exist" in p


class TestBatchSize:
    def test_default_batch_size_is_configurable(self, monkeypatch):
        assert cov.REVIEW_BATCH_SIZE >= 1

    def test_smaller_batches_mean_more_calls_same_verdicts(self):
        """Lowering the batch size must not change what is decided, only how it's asked."""
        from conftest import FakeLLM
        cases = [{"id": f"c{i}", "title": f"T{i}", "type": "functional", "steps": []}
                 for i in range(6)]
        excerpts = [{"repo": "r", "path": "a.py", "text": "def go(): pass"}]

        def run(bs):
            llm = FakeLLM(response={"cases": [
                {"test_case_id": c["id"], "status": "uncovered",
                 "rationale": "none", "files": []} for c in cases]})
            out = cov.review_code_coverage(llm, "F", "req", cases, excerpts, batch_size=bs)
            return len(llm.calls), {c["test_case_id"]: c["status"] for c in out["cases"]}

        calls_big, verdicts_big = run(6)
        calls_small, verdicts_small = run(2)
        assert calls_small > calls_big          # more calls, more attention per case
        assert verdicts_big == verdicts_small   # identical decisions


class TestHeartbeat:
    """A long sweep must keep reporting liveness or the stale-job sweeper kills it.

    STALE_JOB_TTL_SECONDS defaults to 600 and `sweep_stale_jobs` fails any running job
    whose `updated_at` is older than that. The exhaustive sweep replaced a single pass
    with up to ~44 provider calls per feature, which outlasts the TTL — so the review
    loop has to beat the heartbeat itself.
    """

    def _cases(self, n=12):
        return [{"id": f"c{i}", "title": f"T{i}", "type": "functional", "steps": []}
                for i in range(n)]

    def _many_windows(self):
        # big enough chunks that windowing is forced
        return [_chunk(f"f{i}.ts", 3500) for i in range(9)]

    def test_progress_is_reported_per_window(self):
        from conftest import FakeLLM
        seen = []
        llm = FakeLLM(response={"cases": []})
        cov.review_code_coverage(llm, "login v2", "req", self._cases(),
                                 self._many_windows(), batch_size=12,
                                 progress=seen.append)
        assert seen, "no heartbeat emitted — the sweeper would kill this job"
        assert any("window 1/" in m for m in seen)
        assert any("login v2" in m for m in seen)

    def test_progress_reported_per_batch_when_a_window_has_several(self):
        from conftest import FakeLLM
        seen = []
        llm = FakeLLM(response={"cases": []})
        cov.review_code_coverage(llm, "F", "req", self._cases(12),
                                 self._many_windows(), batch_size=3,
                                 progress=seen.append)
        assert any("batch 1/" in m for m in seen)
        assert any("batch 4/" in m for m in seen)

    def test_a_broken_callback_cannot_break_the_review(self):
        from conftest import FakeLLM
        def boom(_m):
            raise RuntimeError("UI blew up")
        llm = FakeLLM(response={"cases": []})
        out = cov.review_code_coverage(llm, "F", "req", self._cases(2),
                                       self._many_windows(), progress=boom)
        assert len(out["cases"]) == 2          # review still completed

    def test_no_callback_is_fine(self):
        from conftest import FakeLLM
        llm = FakeLLM(response={"cases": []})
        out = cov.review_code_coverage(llm, "F", "req", self._cases(2),
                                       self._many_windows())
        assert len(out["cases"]) == 2
