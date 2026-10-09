"""Teardown registry — load, validate and index business teardowns."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TEARDOWNS_DIR = Path(__file__).parent
FIX_IDS = {
    "FIX-MISSED-INBOUND", "FIX-NOSHOW", "FIX-MARKETPLACE-TAX",
    "FIX-UNPRICED-EXTRAS", "FIX-COMPLIANCE-DRIFT", "FIX-SILENT-CHURN",
}


@dataclass
class Teardown:
    teardown_id: str
    template_id: str
    vertical: str
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def top_pain(self) -> dict[str, Any]:
        pains = sorted(self.raw.get("pain_ranking", []), key=lambda p: p["rank"])
        return pains[0] if pains else {}

    @property
    def fix_ids(self) -> list[str]:
        return [p["fix_id"] for p in self.raw.get("pain_ranking", [])]


class TeardownRegistry:
    REQUIRED_KEYS = ("teardown_id", "template_id", "vertical", "acquisition",
                     "margin_leaks", "compliance_spine", "pain_ranking")

    def __init__(self, teardowns_dir: Path | None = None):
        self._dir = teardowns_dir or TEARDOWNS_DIR
        self._cache: dict[str, Teardown] = {}

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("td-*.json"))

    def load(self, teardown_id: str) -> Teardown:
        if teardown_id in self._cache:
            return self._cache[teardown_id]
        path = self._dir / f"{teardown_id}.json"
        if not path.exists():
            raise KeyError(f"unknown teardown: {teardown_id}")
        raw = json.loads(path.read_text())
        self._validate(raw)
        td = Teardown(teardown_id=raw["teardown_id"], template_id=raw["template_id"],
                      vertical=raw["vertical"], raw=raw)
        self._cache[teardown_id] = td
        return td

    def load_all(self) -> list[Teardown]:
        return [self.load(tid) for tid in self.list_ids()]

    def _validate(self, raw: dict[str, Any]) -> None:
        missing = [k for k in self.REQUIRED_KEYS if k not in raw]
        if missing:
            raise ValueError(f"teardown missing keys: {missing}")
        if not raw.get("margin_leaks"):
            raise ValueError("teardown needs ≥1 margin leak")
        ranks = [p["rank"] for p in raw.get("pain_ranking", [])]
        if sorted(ranks) != list(range(1, len(ranks) + 1)):
            raise ValueError("pain ranks must be 1..N contiguous")
        for p in raw.get("pain_ranking", []):
            if p["fix_id"] not in FIX_IDS:
                raise ValueError(f"unknown fix_id: {p['fix_id']}")
        for leak in raw.get("margin_leaks", []):
            if leak.get("stat") and leak.get("stat_basis") not in (
                    "verified-2026", "govt-data", "template-analysis"):
                raise ValueError(f"leak '{leak.get('name')}' has stat without valid basis")

    def pain_index(self) -> dict[str, list[str]]:
        """fix_id → template_ids sharing it. The product story, computed."""
        index: dict[str, list[str]] = {f: [] for f in FIX_IDS}
        for td in self.load_all():
            for fix_id in td.fix_ids:
                if td.template_id not in index[fix_id]:
                    index[fix_id].append(td.template_id)
        return index
