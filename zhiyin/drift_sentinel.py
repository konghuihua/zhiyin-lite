"""
zhiyin-lite: Drift Sentinel
============================
Lightweight behavior drift detector for AI Agents.

Detects 3 types of "capability decay" precursors:
  1. Repeated errors — same error type >=2 times in 3 turns
  2. Skipped checks   — code produced without running review
  3. Tool bloat       — tool calls exceed baseline × 1.8

Usage:
    from zhiyin.drift_sentinel import DriftSentinel

    sentinel = DriftSentinel()
    sentinel.record_turn("t1", "code_dev", ["read","write"], [{"type":"SyntaxError"}])
    sentinel.record_turn("t2", "code_dev", ["edit","exec"], [{"type":"SyntaxError"}])
    result = sentinel.check(intent="code_dev", tools_so_far=["write","exec","exec","exec","exec","exec","exec","exec","exec"])
    if result["triggered"]:
        print(result["suggestion"])
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import Counter


# ── Default baselines (tools per turn for each task type) ──
DEFAULT_BASELINES = {
    "code_dev": 6,
    "research": 8,
    "diagnose": 6,
    "deploy": 5,
    "idle": 4,
}

DEFAULT_WINDOW = 3          # Look-back window (turns)
DEFAULT_REPEAT_COUNT = 2    # Same error >= N triggers warning
DEFAULT_BLOAT_FACTOR = 1.8  # tool calls > baseline × N triggers warning

# Code-producing tools
CODE_TOOLS = {"write", "edit", "patch"}


@dataclass
class TurnRecord:
    turn_id: str
    intent: str
    tools: List[str]
    tool_count: int
    errors: List[dict]
    gates_passed: List[str]


class DriftSentinel:
    """Lightweight behavior drift detector.

    Plugs into any Agent framework. Feed it turn records, ask it to check
    for drift patterns. No external dependencies, no database, no persistence
    by default (add your own logger if needed).
    """

    def __init__(
        self,
        *,
        window: int = DEFAULT_WINDOW,
        repeat_count: int = DEFAULT_REPEAT_COUNT,
        bloat_factor: float = DEFAULT_BLOAT_FACTOR,
        baselines: dict = None,
        code_tools: set = None,
        on_warning: callable = None,
    ):
        self.window = window
        self.repeat_count = repeat_count
        self.bloat_factor = bloat_factor
        self.baselines = baselines or DEFAULT_BASELINES
        self.code_tools = code_tools or CODE_TOOLS
        self.on_warning = on_warning  # callback(warnings) for custom handling

        self.history: List[TurnRecord] = []
        self.max_history = 20
        self.warnings_issued = 0

    # ── Core API ──

    def record_turn(
        self,
        turn_id: str,
        intent: str = "idle",
        tools: List[str] = None,
        errors: List[dict] = None,
        gates_passed: List[str] = None,
    ):
        """Record one turn's behavior fingerprint."""
        record = TurnRecord(
            turn_id=turn_id,
            intent=intent or "idle",
            tools=tools or [],
            tool_count=len(tools) if tools else 0,
            errors=errors or [],
            gates_passed=gates_passed or [],
        )
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def check(
        self,
        intent: str = None,
        tools_so_far: List[str] = None,
        gates_passed: List[str] = None,
    ) -> dict:
        """Check current turn against recent history for drift patterns.

        Returns:
            {
                "triggered": bool,
                "warnings": [{"type": str, "detail": str, "severity": str}],
                "suggestion": str,
            }
        """
        warnings: List[dict] = []
        recent = self.history[-self.window:]

        # ── Pattern 1: Repeated errors ──
        all_errors = []
        for turn in recent:
            all_errors.extend(turn.errors)
        if all_errors:
            error_types = []
            for e in all_errors:
                if isinstance(e, dict):
                    error_types.append(e.get("type", e.get("category", str(e)[:60])))
                else:
                    error_types.append(str(e)[:60])
            freq = Counter(error_types)
            for err_type, count in freq.items():
                if count >= self.repeat_count:
                    warnings.append({
                        "type": "repeated_error",
                        "detail": f"Error pattern '{err_type}' occurred {count} times in {self.window} turns",
                        "severity": "high",
                    })

        # ── Pattern 2: Skipped gate checks ──
        if intent in ("code_dev", "code_test"):
            gates_this_turn = gates_passed or []
            tools_flat = tools_so_far or []
            code_written = any(t in self.code_tools for t in tools_flat)
            if code_written and "gate" not in gates_this_turn:
                warnings.append({
                    "type": "skipped_gate",
                    "detail": "Code produced (write/edit) but no gate check was run",
                    "severity": "critical",
                })

        # ── Pattern 3: Tool call bloat ──
        baseline = self.baselines.get(intent, self.baselines.get("idle", 4))
        tool_count = len(tools_so_far) if tools_so_far else 0
        if tool_count > baseline * self.bloat_factor:
            warnings.append({
                "type": "tool_bloat",
                "detail": f"Tool calls ({tool_count}) exceed {intent} baseline ({baseline}) × {self.bloat_factor}",
                "severity": "warn",
            })

        triggered = len(warnings) > 0
        suggestion = self._suggest(warnings) if triggered else ""

        if triggered:
            self.warnings_issued += 1
            if self.on_warning:
                try:
                    self.on_warning(warnings)
                except Exception:
                    pass

        return {
            "triggered": triggered,
            "warnings": warnings,
            "suggestion": suggestion,
        }

    def _suggest(self, warnings: List[dict]) -> str:
        parts = []
        for w in warnings:
            if w["type"] == "repeated_error":
                parts.append("Repeated error pattern detected. Pause and do root cause analysis.")
            elif w["type"] == "skipped_gate":
                parts.append("Code produced without gate check. Run code review before proceeding.")
            elif w["type"] == "tool_bloat":
                parts.append("Too many tool calls. You may be in a trial-and-error loop. Return to plan.")
        return " | ".join(parts)

    # ── Helpers ──

    def stats(self) -> dict:
        recent_intents = [h.intent for h in self.history[-5:]]
        recent_counts = [h.tool_count for h in self.history[-5:]]
        return {
            "turns_recorded": len(self.history),
            "warnings_issued": self.warnings_issued,
            "recent_intents": recent_intents,
            "recent_tool_counts": recent_counts,
            "avg_tool_count": sum(recent_counts) / len(recent_counts) if recent_counts else 0,
        }

    def reset(self):
        self.history.clear()
        self.warnings_issued = 0

    def __repr__(self):
        return f"DriftSentinel(turns={len(self.history)}, warnings={self.warnings_issued})"
