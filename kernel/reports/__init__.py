"""Reports package — schema-validated state documents + markdown renderer."""
from .registry import ReportRegistry, VALID_KINDS, render_markdown

__all__ = ["ReportRegistry", "VALID_KINDS", "render_markdown"]
