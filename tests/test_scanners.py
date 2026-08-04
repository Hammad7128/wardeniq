"""Tests for the optional deterministic-scanner layer.

The scanners themselves (semgrep / gitleaks) are not test dependencies, so these assert
the two things that must hold regardless of whether the binaries exist: absence degrades
cleanly, and corroboration is attached without ever changing a verdict.
"""
import scanners


class TestAvailability:
    def test_missing_scanner_is_reported_not_raised(self, monkeypatch):
        monkeypatch.setattr(scanners.shutil, "which", lambda _n: None)
        assert scanners.scanner_available("semgrep") is False
        assert scanners.available_scanners() == []
        r = scanners.run_semgrep([{"repo": "r", "path": "a.py", "text": "x=1"}])
        assert r == {"available": False, "scanner": "semgrep", "findings": []}

    def test_scan_excerpts_reports_missing_and_never_raises(self, monkeypatch):
        monkeypatch.setattr(scanners.shutil, "which", lambda _n: None)
        out = scanners.scan_excerpts([{"repo": "r", "path": "a.py", "text": "x=1"}])
        assert out["scanners_run"] == []
        assert sorted(out["scanners_missing"]) == ["gitleaks", "semgrep"]
        assert out["findings"] == [] and out["by_path"] == {}

    def test_scanner_exception_is_contained(self, monkeypatch):
        def boom(_excerpts):
            raise RuntimeError("scanner exploded")
        monkeypatch.setattr(scanners, "run_semgrep", boom)
        out = scanners.scan_excerpts([{"repo": "r", "path": "a.py", "text": "x=1"}],
                                     enabled=("semgrep",))
        assert out["findings"] == []
        assert any("scanner exploded" in e for e in out["errors"])


class TestMaterialize:
    def test_writes_relative_paths(self, tmp_path):
        written = scanners._materialize(
            [{"repo": "r", "path": "pkg/mod.py", "text": "def f(): pass"}], str(tmp_path))
        assert "pkg/mod.py" in written
        assert (tmp_path / "pkg" / "mod.py").read_text() == "def f(): pass"

    def test_concatenates_multiple_chunks_of_one_file(self, tmp_path):
        scanners._materialize([
            {"repo": "r", "path": "a.py", "text": "first"},
            {"repo": "r", "path": "a.py", "text": "second"},
        ], str(tmp_path))
        body = (tmp_path / "a.py").read_text()
        assert "first" in body and "second" in body

    def test_path_traversal_is_refused(self, tmp_path):
        written = scanners._materialize(
            [{"repo": "r", "path": "../../etc/passwd", "text": "bad"}], str(tmp_path))
        assert written == {}

    def test_absolute_path_is_refused(self, tmp_path):
        written = scanners._materialize(
            [{"repo": "r", "path": "/etc/passwd", "text": "bad"}], str(tmp_path))
        # leading slash is stripped to a relative path, so it stays inside the sandbox
        assert all(not p.startswith("/") for p in written)
        assert not (tmp_path / ".." / "etc" / "passwd").exists()

    def test_respects_the_byte_budget(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scanners, "_MAX_SCAN_BYTES", 10)
        written = scanners._materialize([
            {"repo": "r", "path": "a.py", "text": "x" * 8},
            {"repo": "r", "path": "b.py", "text": "y" * 8},
        ], str(tmp_path))
        assert list(written) == ["a.py"]

    def test_skips_empty_entries(self, tmp_path):
        assert scanners._materialize(
            [{"repo": "r", "path": "", "text": "x"}, {"repo": "r", "path": "a.py", "text": ""}],
            str(tmp_path)) == {}


class TestCorroborate:
    SCAN = {"by_path": {"app/auth/login.py": [
        {"scanner": "semgrep", "rule": "python.lang.security.audit.weak-hash",
         "severity": "WARNING", "message": "weak hash", "path": "app/auth/login.py"}]}}

    def test_attaches_findings_to_a_matching_citation(self):
        cases = [{"test_case_id": "c1", "status": "covered",
                  "files": ["api:app/auth/login.py"]}]
        out = scanners.corroborate(cases, self.SCAN)
        assert out[0]["scanner_findings"][0]["rule"].endswith("weak-hash")

    def test_never_changes_a_verdict(self):
        cases = [{"test_case_id": "c1", "status": "covered",
                  "files": ["api:app/auth/login.py"]}]
        out = scanners.corroborate(cases, self.SCAN)
        assert out[0]["status"] == "covered"      # advisory only, by design

    def test_no_findings_leaves_cases_untouched(self):
        cases = [{"test_case_id": "c1", "status": "partial", "files": ["api:other.py"]}]
        out = scanners.corroborate(cases, self.SCAN)
        assert "scanner_findings" not in out[0]

    def test_absence_of_findings_is_not_recorded_as_clean(self):
        # "no scanner hit" must never be stored as positive evidence of correctness.
        cases = [{"test_case_id": "c1", "status": "partial", "files": []}]
        out = scanners.corroborate(cases, {"by_path": {}})
        assert "scanner_findings" not in out[0]
        assert out[0] == {"test_case_id": "c1", "status": "partial", "files": []}

    def test_matches_on_basename_when_repo_prefix_differs(self):
        cases = [{"test_case_id": "c1", "status": "covered", "files": ["login.py"]}]
        out = scanners.corroborate(cases, self.SCAN)
        assert out[0].get("scanner_findings")

    def test_empty_scan_is_a_noop(self):
        cases = [{"test_case_id": "c1", "files": ["a.py"]}]
        assert scanners.corroborate(cases, {}) == cases
