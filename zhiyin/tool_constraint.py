"""
zhiyin-lite: Tool Constraint Checker
=====================================
Plugs into any Agent framework to intercept and validate tool calls.

Combines StateMachine + ToolTrie to answer one question:
  "Should the agent be allowed to call this tool right now?"

Usage:
    from zhiyin.tool_constraint import ToolConstraintChecker
    from zhiyin.state_machine import StateMachine

    sm = StateMachine()
    sm.add_state("code", tools=["read","write","exec"], forbidden=["gateway"])

    checker = ToolConstraintChecker(sm)
    checker.transition_to("code")

    result = checker.check("exec", {"command": "python3 test.py"})
    # result.allowed == True

    result = checker.check("gateway", {"action": "restart"})
    # result.allowed == False — gateway is forbidden in code state
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .state_machine import StateMachine, Severity


# ── Intent classification keywords ──
INTENT_KEYWORDS = {
    "code_dev": [
        "write", "code", "fix", "bug", "implement", "refactor", "optimize",
        "build", "develop", "create", "add", "change", "modify", "update",
        "写", "代码", "修复", "开发", "实现", "重构", "优化",
    ],
    "research": [
        "search", "find", "research", "compare", "analyze", "explore",
        "look up", "what is", "how to", "调查", "搜索", "分析", "对比",
    ],
    "deploy": [
        "deploy", "release", "publish", "ship", "restart", "deploy",
        "部署", "发布", "上线", "重启",
    ],
    "diagnose": [
        "why", "error", "bug", "fail", "crash", "broken", "debug",
        "diagnose", "troubleshoot", "怎么回事", "出错", "报错", "排查",
    ],
}


@dataclass
class CheckResult:
    blocked: bool
    allowed: bool = True
    reason: str = ""
    suggestion: str = ""
    violation_count: int = 0
    severity: str = "info"


class ToolConstraintChecker:
    """Intercept and validate tool calls against a StateMachine."""

    def __init__(self, state_machine: StateMachine):
        self.sm = state_machine
        self.violation_count = 0
        self.consecutive_violations = 0
        self.max_consecutive_before_escalate = 3

    # ── Intent classification ──

    def classify_intent(self, user_message: str) -> str:
        """Guess task intent from user message keywords."""
        msg = user_message.lower()
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            scores[intent] = sum(1 for kw in keywords if kw in msg)
        if not scores:
            return "idle"
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "idle"

    def auto_transition(self, user_message: str) -> str:
        """Classify intent and auto-transition state machine."""
        intent = self.classify_intent(user_message)
        if intent != "idle":
            self.sm.transition_to(intent)
        return intent

    # ── Tool check ──

    def check(self, tool_name: str, params: dict = None) -> CheckResult:
        """Check if a tool call is allowed in current state."""
        result = self.sm.can_call(tool_name, params)

        if not result.allowed:
            self.violation_count += 1
            self.consecutive_violations += 1
            return CheckResult(
                blocked=True,
                allowed=False,
                reason=result.reason,
                suggestion=result.suggestion,
                violation_count=self.violation_count,
                severity=result.severity.value,
            )

        self.consecutive_violations = 0
        return CheckResult(allowed=True)

    def check_escalation(self) -> dict:
        """If violations are piling up, suggest escalation."""
        if self.consecutive_violations >= self.max_consecutive_before_escalate:
            return {
                "escalate": True,
                "level": "warn",
                "message": f"{self.consecutive_violations} consecutive violations. "
                           "Consider rolling back to a safe state.",
                "suggested_action": "rollback",
            }
        return {"escalate": False}

    # ── Helpers ──

    def transition_to(self, state: str) -> dict:
        return self.sm.transition_to(state)

    def force_state(self, state: str):
        self.sm.current_state = state
        self.consecutive_violations = 0

    def reset(self):
        self.sm.reset()
        self.violation_count = 0
        self.consecutive_violations = 0

    def summary(self) -> dict:
        return {
            "state": self.sm.current_state,
            "violations": self.violation_count,
            "consecutive": self.consecutive_violations,
            "escalation": self.check_escalation(),
        }

    def __repr__(self):
        return f"ToolConstraintChecker(state='{self.sm.current_state}', violations={self.violation_count})"
