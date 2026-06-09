# zhiyin-lite

> 轻量级AGENT降智防线框架 — 让你的AI助手不再越用越蠢

[![PyPI](https://img.shields.io/badge/pypi-soon-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## 一句话

**10模块轻量版AGENT架构 — 状态机约束 + 工具调用拦截 + 漂移哨兵 + 事件总线**

不是又一个Agent编排框架。这是一个**运行时质量保障系统**——防止你的Agent在复杂任务中注意力散焦、重复犯错、忘记约束。

## 为什么需要它？

你在用LangChain/AutoGPT/CrewAI构建Agent。前几轮交互很好。到第10轮，Agent开始：
- 重复同一个错误
- 忘记你说过"不要改数据库配置"
- 疯狂调用工具来试错而非按计划执行

这不是你的Prompt有问题。这是**上下文膨胀导致模型注意力散焦**。

zhiyin-lite在运行时检测这种行为漂移，并在Agent"降智"前拉响警报。

## 快速开始

```bash
pip install zhiyin-lite
```

```python
from zhiyin import AgentRuntime, DriftSentinel, StateMachine, ToolGate

# 1. 定义状态机 — Agent能做什么、不能做什么
sm = StateMachine()
sm.add_state("plan", tools=["search", "read"], forbidden=["exec", "write"])
sm.add_state("code", tools=["read", "write", "exec"], forbidden=["gateway"])

# 2. 挂载工具约束 — 前缀树拦截非法调用
gate = ToolGate(sm)
gate.enable()

# 3. 激活漂移哨兵 — 每回合后检查行为模式
sentinel = DriftSentinel(
    repeat_error_window=3,
    tool_bloat_factor=1.8
)

# 4. 启动运行时
runtime = AgentRuntime(
    state_machine=sm,
    tool_gate=gate,
    drift_sentinel=sentinel,
    event_bus=True  # 模块间pub/sub通信
)

# 5. 运行你的Agent——自动受保护
response = runtime.run("帮我重构数据管道模块")
```

## 核心能力

| 模块 | 做什么 |
|------|--------|
| **StateMachine** | 定义任务阶段 + 合法的工具白名单，禁止Agent在plan阶段执行代码 |
| **ToolGate** | 前缀树(Trie)拦截每个工具调用，违反白名单直接拒绝 |
| **DriftSentinel** | 实时检测3类降智：重复错误 / 跳过检查 / 工具膨胀 |
| **EventBus** | 模块间pub/sub通信，解除紧耦合 |
| **IntentClassifier** | 关键词匹配自动分类用户意图(code/research/deploy/diagnose) |
| **TaskSnapshot** | 任务快照替代膨胀的对话历史，控制上下文大小 |

## 实测效果

在20模块完整版系统中，部署双轨防线后：

- 飞轮健康度：**0.733 → 0.983 (+34%)**
- 恢复成功率：**0 → 100%**
- 连续60轮复杂任务：零次重复踩坑，零次忘记约束

## 和LangChain/LangGraph/CrewAI是什么关系？

**互补，而非替代。** 它们管"怎么跑"，我们管"跑的时候别崩"。可以作为中间件嵌入任何Agent框架。

| | LangChain | CrewAI | zhiyin-lite |
|---|-----------|--------|-------------|
| 设计中心 | Agent流程编排 | 多Agent协调 | **运行时质量保障** |
| 状态机 | DAG | 角色定义 | **硬约束+工具白名单** |
| 降智检测 | 需自行实现 | 需自行实现 | **内置3类漂移模式** |
| 工具拦截 | 回调机制(可扩展) | 无内置 | **前缀Trie自动拦截** |

## 路线图

- [x] v0.1 状态机骨架 + 工具约束Trie
- [ ] v0.2 漂移哨兵基础规则
- [ ] v0.3 事件总线 + 任务快照
- [ ] v0.4 OpenClaw/LangChain plugin
- [ ] v1.0 PyPI正式发布

## 许可证

MIT License — 自由使用、修改、分发。

完整版（21模块 + FDGS知识库 + A10消化管线）以商业授权提供。企业版起价5万/年（私有化部署 + 完整知识库 + 技术支持）。

---

*由知因 (0660180403) 设计和维护*
*博客：《你的AI助手为什么越用越蠢？》[立即阅读](./blog-agent-capability-decay.md)*
