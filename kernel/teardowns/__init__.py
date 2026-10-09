"""Teardown package — six-question interrogation per template."""
from .registry import Teardown, TeardownRegistry, FIX_IDS
from .graph import (build_meta_graph, pains_in_pattern, compliance_recurrence,
                    stats_for_fix, VERTICAL_PATTERN)

__all__ = ["Teardown", "TeardownRegistry", "FIX_IDS", "build_meta_graph",
           "pains_in_pattern", "compliance_recurrence", "stats_for_fix",
           "VERTICAL_PATTERN"]
