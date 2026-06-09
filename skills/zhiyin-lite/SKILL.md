---
name: zhiyin-lite
description: Agent capability decay defense — state machine, tool constraint, drift sentinel
version: 0.1.0
author: 知因 (0660180403)
license: MIT
homepage: https://github.com/konghuihua/zhiyin-lite
tags:
  - agent
  - state-machine
  - tool-constraint
  - drift-detection
  - quality
platforms:
  - openclaw
  - claude-code
  - codex
---

# zhiyin-lite — Agent Capability Decay Defense

Your AI agent gets dumber during long tasks because context inflation dilutes attention. zhiyin-lite detects and prevents this in real-time.

## What it does

Three lightweight modules that plug into any Agent framework:

| Module | Purpose |
|--------|---------|
| **StateMachine** | Define task phases + tool allowlists. Model can't call tools outside current phase. |
| **DriftSentinel** | After each turn, scan for 3 decay patterns: repeated errors, skipped checks, tool bloat. |
| **ToolConstraintChecker** | Intercept tool calls against StateMachine + exec pattern filter + consecutive call limits. |

## Quick Install

```bash
pip install zhiyin-lite
```

## Usage (5 lines)

```python
from zhiyin import StateMachine, DriftSentinel, ToolConstraintChecker

sm = StateMachine()
sm.add_state("plan", tools=["search","read"], forbidden=["exec","write"])
sm.add_state("code", tools=["read","write","exec"], forbidden=["gateway"])
sm.transition_to("plan")

sentinel = DriftSentinel()
sentinel.record_turn("t1", "code_dev", ["read","write"], [{"type":"SyntaxError"}])

checker = ToolConstraintChecker(sm)
result = checker.check("gateway", {"action":"restart"})
# result.allowed = False — gateway blocked in plan state
```

## When to use this skill

Use this skill when:
- User reports Agent "getting dumber" over time
- Agent repeats the same error across multiple turns
- Agent skips quality checks (code review, tests)
- Agent calls too many tools in one turn (trial-and-error loops)
- Building or debugging Agent frameworks
- Integrating state-machine governance into an AI pipeline

## Architecture

```
User Intent
  │
  ├─ StateMachine.transition_to(intent)  — lock tools to current phase
  ├─ ToolConstraintChecker.check(tool)    — intercept every tool call
  ├─ Agent runs (model inference)
  ├─ DriftSentinel.record_turn(...)       — log behavior fingerprint
  └─ DriftSentinel.check(...)             — detect decay, inject warning
```

## Integration with OpenClaw

zhiyin-lite works as a middleware between OpenClaw and your Agent. Example hook:

```python
# In your before_tool_call hook:
from zhiyin import ToolConstraintChecker

checker = ToolConstraintChecker(sm)

def before_tool_call(tool_name, params):
    result = checker.check(tool_name, params)
    if result.blocked:
        return {"error": result.reason}
    return None  # allow
```

## Enterprise

Full version (21-module system + FDGS knowledge base 27,957 entries + A10 digestion pipeline) available under commercial license. Contact for details.

## Learn More

- GitHub: https://github.com/konghuihua/zhiyin-lite
- Blog (Chinese): 《你的AI助手为什么越用越蠢？》
- Blog (English): "Why Your AI Agent Gets Dumber Over Time — And How to Fix It"
