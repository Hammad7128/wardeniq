"""Regression coverage for the Test Cycle PDF export's Category/Priority overlap bug.

QA report: "Category column text overlaps with the Priority column in the
exported PDF" — reproduced specifically with the "Business / Functional"
category, on any cycle item whose category label is long.

Root cause (confirmed by actually rendering the PDF and inspecting glyph
positions with pdfplumber during investigation — not just read the code):
`build_cycle_pdf()`'s row-building code wrapped the ID and Title cells in
`Paragraph(...)` but passed Category/Priority/Status as *plain strings*.
reportlab's `Table` only wraps or clips Flowable cell content (like a
Paragraph) to the column width; a bare string wider than its column is drawn
past the column's right edge with no wrapping and no clipping. At 8pt in the
24mm-wide Category column, "Business / Functional" and "Edge & Reliability"
are wide enough to run into the Priority column's own text — badly enough
that in the rendered PDF the glyphs from "Functional" and "High" literally
interleave into "FunctionHailgh". Short labels like "API" happened to fit
their column, which is why this wasn't caught for every category.

The fix wraps Category/Priority/Status in the same `Paragraph(..., cell)`
already used for ID/Title, so reportlab wraps them to the column width instead
of overflowing. This test doesn't re-render pixels (that was verified by hand
against a real generated PDF during the fix, using pdfplumber — not part of
this repo's dependencies, so not added here); it pins the structural
invariant that regressed: every non-numeric cell in a data row must be a
Paragraph, never a bare string, so a future edit can't silently reintroduce
the overflow.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from reportlab.platypus import Paragraph  # noqa: E402

import report  # noqa: E402


def _cycle_with_long_categories():
    return {
        "name": "Sprint 12 Regression",
        "status": "active",
        "items": [
            {
                "display_order": "1", "display_id": "NEA-CEF2-6", "case_id": "c1",
                "title": "Score an event for participation likelihood",
                "category": "functional",   # -> "Business / Functional" (long)
                "priority": "P1",
                "execution_status": "failed",
            },
            {
                "display_order": "2", "display_id": "NEA-CEF2-18", "case_id": "c2",
                "title": "User modifies event details after low participation feedback",
                "category": "nfr",          # -> "Edge & Reliability" (long)
                "priority": "P2",
                "execution_status": "untested",
            },
            {
                "display_order": "3", "display_id": "NEA-ED2-1", "case_id": "c3",
                "title": "Successful retrieval of nearby events with default parameters",
                "category": "api",          # -> "API" (short -- didn't trigger the bug)
                "priority": "P1",
                "execution_status": "untested",
            },
        ],
    }


def test_category_priority_status_cells_are_paragraphs_not_bare_strings(monkeypatch):
    """The actual invariant that broke: every data-row cell reportlab is asked
    to lay out into a fixed-width column must be a Paragraph (wraps/clips to
    that width), never a plain string (draws past the column with no wrap)."""
    captured_rows = []
    real_table = report.Table

    def spy_table(rows, *a, **k):
        captured_rows.append(rows)
        return real_table(rows, *a, **k)

    monkeypatch.setattr(report, "Table", spy_table)

    pdf_bytes = report.build_cycle_pdf(_cycle_with_long_categories())
    assert pdf_bytes.startswith(b"%PDF"), "build_cycle_pdf() must still produce a real PDF"

    assert len(captured_rows) == 1
    rows = captured_rows[0]
    header, data_rows = rows[0], rows[1:]
    assert header == ["#", "ID", "Title", "Category", "Priority", "Status"]
    assert len(data_rows) == 3

    for row in data_rows:
        num, rid, title, category, priority, status = row
        # "#" is a short numeric index -- never long enough to overflow its
        # 9mm column, so it's the one cell allowed to stay a plain string.
        assert isinstance(num, str)
        for label, cell in [("ID", rid), ("Title", title), ("Category", category),
                             ("Priority", priority), ("Status", status)]:
            assert isinstance(cell, Paragraph), (
                f"{label} cell is a bare string ({cell!r}) instead of a Paragraph -- "
                "reportlab won't wrap/clip it to the column width, which is exactly "
                "how the Category/Priority overlap bug happened."
            )


def test_long_category_labels_render_without_raising():
    """Smoke-test the exact QA repro inputs (functional/nfr categories) end to
    end through the real function -- not just the row-construction internals."""
    pdf_bytes = report.build_cycle_pdf(_cycle_with_long_categories())
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
