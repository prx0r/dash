"""Distill registry + runner — op definitions, validation, chained execution."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

OPS_DIR = Path(__file__).parent / "ops"

EXECUTORS: dict[str, Callable] = {}


def register(op_id: str):
    def deco(fn: Callable):
        EXECUTORS[op_id] = fn
        return fn
    return deco


class DistillRegistry:
    REQUIRED = ("op_id", "version", "description", "inputs", "outputs",
                "side_effect", "deterministic", "sources")

    def __init__(self, ops_dir: Path | None = None):
        self._dir = ops_dir or OPS_DIR
        self._cache: dict[str, dict] = {}

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("distill-*.json"))

    def load(self, op_id: str) -> dict:
        if op_id not in self._cache:
            path = self._dir / f"{op_id}.json"
            if not path.exists():
                raise KeyError(f"unknown op: {op_id}")
            raw = json.loads(path.read_text())
            missing = [k for k in self.REQUIRED if k not in raw]
            if missing:
                raise ValueError(f"op {op_id} missing: {missing}")
            if not (0 <= raw["side_effect"] <= 5):
                raise ValueError(f"op {op_id}: bad side_effect")
            self._cache[op_id] = raw
        return self._cache[op_id]

    def load_all(self) -> list[dict]:
        return [self.load(i) for i in self.list_ids()]


def _wire_executors() -> None:
    from . import executors as ex

    EXECUTORS.setdefault("distill-sprawl-scan",
                         lambda ctx: ex.sprawl_scan(ctx["inventory"]))
    EXECUTORS.setdefault("distill-cluster",
                         lambda ctx: ex.cluster(ctx["candidates"]))
    EXECUTORS.setdefault("distill-snowball",
                         lambda ctx: ex.snowball(ctx["thesis"],
                                                 ctx["evidence_batch"]))
    EXECUTORS.setdefault("distill-gate-check",
                         lambda ctx: ex.gate_check(ctx["candidate"]))
    EXECUTORS.setdefault("distill-campaign-compile",
                         lambda ctx: ex.campaign_compile(
                             ctx["eligible"], ctx.get("template")))
    EXECUTORS.setdefault("distill-refine",
                         lambda ctx: ex.refine(ctx["outcome"]))


def run_chain(op_ids: list[str], context: dict[str, Any]) -> dict[str, Any]:
    """Execute ops in order over a shared context. Receipt per op."""
    _wire_executors()
    receipts: list[dict] = []
    outputs: dict[str, Any] = {}
    for op_id in op_ids:
        if op_id not in EXECUTORS:
            raise KeyError(f"no executor: {op_id}")
        merged = {**context, **outputs}
        result = EXECUTORS[op_id](merged)
        outputs[op_id] = result
        receipts.append({
            "op_id": op_id,
            "at": time.time(),
            "output_hash": hashlib.sha256(
                json.dumps(result, sort_keys=True,
                           default=str).encode()).hexdigest()[:12],
        })
    return {"outputs": outputs, "receipts": receipts}
