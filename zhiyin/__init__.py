"""
zhiyin-lite — Lightweight Agent Capability Decay Defense

See README.md for full documentation.
"""

from .state_machine import StateMachine, ToolTrie, Severity
from .drift_sentinel import DriftSentinel
from .tool_constraint import ToolConstraintChecker

__version__ = "0.1.0"
__all__ = [
    "StateMachine",
    "ToolTrie",
    "Severity",
    "DriftSentinel",
    "ToolConstraintChecker",
]
