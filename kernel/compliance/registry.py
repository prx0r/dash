"""Compliance registry — legislation pack with basis enforcement."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

COMPLIANCE_DIR = Path(__file__).parent
ALLOWED_BASIS = {"verified-2026", "well-established", "template-analysis"}


@dataclass
class Legislation:
    id: str
    law: str
    basis: str
    verticals: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class ComplianceRegistry:
    def __init__(self, path: Path | None = None):
        self._path = path or (COMPLIANCE_DIR / "legislation.json")
        self._cache: list[Legislation] | None = None

    def load_all(self) -> list[Legislation]:
        if self._cache is None:
            raw = json.loads(self._path.read_text())["legislation"]
            self._cache = [Legislation(id=e["id"], law=e["law"], basis=e["basis"],
                                       verticals=e.get("verticals", []), raw=e)
                           for e in raw]
        return self._cache

    def for_vertical(self, vertical: str) -> list[Legislation]:
        return [e for e in self.load_all() if vertical in e.verticals]

    def verified(self) -> list[Legislation]:
        return [e for e in self.load_all() if e.basis == "verified-2026"]
