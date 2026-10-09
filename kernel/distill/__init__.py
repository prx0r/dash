"""distillprotocol — BigQuery sprawl → campaigns/theses, as runnable ops."""
from .registry import DistillRegistry, run_chain, EXECUTORS
from . import executors

__all__ = ["DistillRegistry", "run_chain", "EXECUTORS", "executors"]
