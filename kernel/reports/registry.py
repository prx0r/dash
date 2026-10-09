"""Reports — structured state-of-X documents, schema-validated, rendered to markdown."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_KINDS = {"executive-summary", "inventory", "census", "proof", "gaps",
               "tiers", "verdicts", "honesty", "next-steps", "sources",
               "formula"}


class ReportRegistry:
    REQUIRED = ("report_id", "title", "date", "status", "sections")

    def validate(self, report: dict[str, Any]) -> list[str]:
        """Returns error list (empty = valid)."""
        errors = []
        for k in self.REQUIRED:
            if k not in report:
                errors.append(f"missing: {k}")
        for i, s in enumerate(report.get("sections", [])):
            if s.get("kind") not in VALID_KINDS:
                errors.append(f"section {i}: bad kind {s.get('kind')}")
            if not s.get("heading"):
                errors.append(f"section {i}: missing heading")
            for t in s.get("tables", []):
                if not t.get("columns") or "rows" not in t:
                    errors.append(f"section {i}: malformed table")
                for r in t.get("rows", []):
                    if len(r) != len(t["columns"]):
                        errors.append(f"section {i}: row/column mismatch {r}")
        return errors


def render_markdown(report: dict[str, Any]) -> str:
    """Report JSON → markdown following the drop report spine."""
    lines = [f"# {report['title']}", "",
             f"**Date:** {report['date']}", f"**Status:** {report['status']}",
             f"**Report ID:** `{report['report_id']}`", "", "---", ""]
    n = 0
    for s in report["sections"]:
        n += 1
        lines += [f"## {n}. {s['heading']}", ""]
        if s.get("body"):
            lines += [s["body"], ""]
        for t in s.get("tables", []):
            cols = t["columns"]
            lines.append("| " + " | ".join(cols) + " |")
            lines.append("|" + "|".join(["---"] * len(cols)) + "|")
            for r in t["rows"]:
                lines.append("| " + " | ".join(str(c) for c in r) + " |")
            lines.append("")
        for q in s.get("queries", []):
            lines += ["```sql", q["sql"], "```",
                      f"→ {q['result']}", ""]
    return "\n".join(lines)
