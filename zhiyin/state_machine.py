"""
zhiyin-lite: State Machine Engine
==================================
A lightweight, pluggable state machine for AI Agent tool-call governance.

Core idea: The model doesn't decide what tools it can call — the state machine does.

Usage:
    from zhiyin.state_machine import StateMachine

    sm = StateMachine()
    sm.add_state("plan", tools=["search", "read"], forbidden=["exec", "write"])
    sm.add_state("code", tools=["read", "write", "exec"], forbidden=["gateway"])

    sm.transition_to("plan")
    sm.can_call("read")   # True
    sm.can_call("exec")   # False — blocked by state
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    INFO = "info"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class State:
    name: str
    allowed_tools: Set[str] = field(default_factory=set)
    forbidden_tools: Set[str] = field(default_factory=set)
    allowed_next: Set[str] = field(default_factory=set)
    max_consecutive_calls: int = 0
    description: str = ""


@dataclass
class ToolCheckResult:
    allowed: bool
    reason: str = ""
    suggestion: str = ""
    severity: Severity = Severity.INFO


class ToolTrie:
    """Prefix tree for O(n) tool-name matching."""

    def __init__(self):
        self.root: dict = {}

    def insert(self, name: str):
        node = self.root
        for ch in name:
            node = node.setdefault(ch, {})
        node["$"] = True

    def search(self, name: str) -> bool:
        node = self.root
        for ch in name:
            if ch not in node:
                return False
            node = node[ch]
        return "$" in node

    def starts_with(self, prefix: str) -> List[str]:
        node = self.root
        for ch in prefix:
            if ch not in node:
                return []
            node = node[ch]
        results: List[str] = []
        self._collect(node, prefix, results)
        return results

    def _collect(self, node: dict, prefix: str, results: List[str]):
        if "$" in node:
            results.append(prefix)
        for ch, child in node.items():
            if ch != "$":
                self._collect(child, prefix + ch, results)


class StateMachine:
    """Lightweight state machine for Agent tool governance.

    Key design decisions:
    - Each state has an allowlist AND a blocklist for tools
    - Transitions are explicit — no implicit fallthrough
    - Built-in patterns: exec command regex filtering, consecutive call limits
    """

    def __init__(self, initial_state: str = "idle"):
        self.current_state = initial_state
        self.states: Dict[str, State] = {}
        self.transition_history: List[dict] = []
        self._consecutive_counts: Dict[str, int] = {}
        self._setup_defaults()

    def _setup_defaults(self):
        """Minimal default states. Users should customize via add_state()."""
        self.add_state(
            "idle",
            tools=["read", "search"],
            forbidden=["exec", "write", "delete"],
            description="Default idle state — safe browsing only"
        )

    # ── State definition ──

    def add_state(
        self,
        name: str,
        *,
        tools: Optional[List[str]] = None,
        forbidden: Optional[List[str]] = None,
        allowed_next: Optional[List[str]] = None,
        max_consecutive_calls: int = 0,
        exec_patterns: Optional[List[str]] = None,
        description: str = "",
    ):
        """Register a new state or update an existing one."""
        s = self.states.get(name, State(name=name))
        if tools:
            s.allowed_tools.update(tools)
        if forbidden:
            s.forbidden_tools.update(forbidden)
        if allowed_next:
            s.allowed_next.update(allowed_next)
        if max_consecutive_calls:
            s.max_consecutive_calls = max_consecutive_calls
        if description:
            s.description = description
        # Store exec patterns as a private attr
        if exec_patterns:
            setattr(s, "_exec_patterns", exec_patterns)
        self.states[name] = s

    def remove_state(self, name: str):
        self.states.pop(name, None)

    # ── Transitions ──

    def can_transition_to(self, target: str) -> bool:
        if target not in self.states:
            return False
        current = self.states.get(self.current_state)
        if not current or not current.allowed_next:
            return True  # No restrictions
        return target in current.allowed_next

    def transition_to(self, target: str) -> dict:
        if target not in self.states:
            return {"ok": False, "reason": f"Unknown state: {target}"}
        if not self.can_transition_to(target):
            allowed = list(self.states[self.current_state].allowed_next) if self.current_state in self.states else []
            return {
                "ok": False,
                "reason": f"Cannot transition from {self.current_state} to {target}",
                "allowed": allowed,
            }
        old = self.current_state
        self.current_state = target
        self._consecutive_counts.clear()
        self.transition_history.append({"from": old, "to": target})
        return {"ok": True, "from": old, "to": target}

    # ── Tool checks ──

    def _build_trie(self) -> ToolTrie:
        trie = ToolTrie()
        state = self.states.get(self.current_state)
        if state:
            for tool in state.allowed_tools:
                if tool not in state.forbidden_tools:
                    trie.insert(tool)
        return trie

    def can_call(self, tool_name: str, params: dict = None) -> ToolCheckResult:
        """Check if a tool call is allowed in the current state."""
        state = self.states.get(self.current_state)
        if not state:
            return ToolCheckResult(allowed=True)  # No restrictions defined

        params = params or {}

        # 1. Direct blocklist check
        if tool_name in state.forbidden_tools:
            return ToolCheckResult(
                allowed=False,
                reason=f"'{tool_name}' is forbidden in state '{self.current_state}'",
                suggestion=f"Allowed: {sorted(state.allowed_tools - state.forbidden_tools)}",
                severity=Severity.BLOCK,
            )

        # 2. Trie allowlist check
        trie = self._build_trie()
        if trie.root and not trie.search(tool_name):
            return ToolCheckResult(
                allowed=False,
                reason=f"'{tool_name}' not in allowlist for state '{self.current_state}'",
                suggestion=f"Try: {sorted(state.allowed_tools - state.forbidden_tools)[:5]}",
                severity=Severity.BLOCK,
            )

        # 3. Exec-specific: command pattern check
        if tool_name == "exec":
            cmd = params.get("command", "")
            exec_patterns = getattr(state, "_exec_patterns", None)
            if cmd and exec_patterns:
                import re
                if not any(re.match(p, cmd) for p in exec_patterns):
                    return ToolCheckResult(
                        allowed=False,
                        reason=f"Exec command not allowed in state '{self.current_state}'",
                        suggestion=f"Command must match one of: {exec_patterns}",
                        severity=Severity.BLOCK,
                    )

        # 4. Consecutive call limit
        if state.max_consecutive_calls > 0:
            cnt = self._consecutive_counts.get(tool_name, 0) + 1
            if cnt > state.max_consecutive_calls:
                return ToolCheckResult(
                    allowed=False,
                    reason=f"Too many consecutive '{tool_name}' calls (limit: {state.max_consecutive_calls})",
                    suggestion="Check results before retrying.",
                    severity=Severity.WARN,
                )

        # Track consecutive calls
        for k in list(self._consecutive_counts):
            if k != tool_name:
                del self._consecutive_counts[k]
        self._consecutive_counts[tool_name] = self._consecutive_counts.get(tool_name, 0) + 1

        return ToolCheckResult(allowed=True)

    # ── Helpers ──

    def get_current_tools(self) -> Set[str]:
        state = self.states.get(self.current_state)
        if not state:
            return set()
        return state.allowed_tools - state.forbidden_tools

    def reset(self):
        self.current_state = "idle"
        self.transition_history.clear()
        self._consecutive_counts.clear()

    def summary(self) -> dict:
        return {
            "current_state": self.current_state,
            "states_defined": len(self.states),
            "allowed_tools": sorted(self.get_current_tools()),
            "transitions": len(self.transition_history),
        }

    def __repr__(self):
        return f"StateMachine(state='{self.current_state}', tools={len(self.get_current_tools())})"
