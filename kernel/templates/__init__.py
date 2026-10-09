"""Vertical templates — graph shapes per business type.

getsocials gives every company the same identity root; templates give it
vertical-specific nodes, edges, workflows and onboarding steps.
Security kernel is shared and never varies.
"""
from .registry import Template, TemplateRegistry

__all__ = ["Template", "TemplateRegistry"]
