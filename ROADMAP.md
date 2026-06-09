# zhiyin-lite 核心模块

轻量版当前提供以下模块的参考实现或接口规范：

## 已就绪 (可直接参考)
- `core/state_machine.py` — 状态机骨架
- `core/tool_constraint.py` — 工具约束Trie
- `core/drift_sentinel.py` — 基础漂移哨兵

## 待提取 (从生产系统精简)
- `core/event_bus.py` — 事件总线协议
- `core/intent_classifier.py` — 意图感知分类
- `core/task_snapshot.py` — 任务快照管理
- `plugins/openclaw_hook.py` — ClawX hook集成
- `plugins/langchain_hook.py` — LangChain中间件

完整生产系统为20+1模块架构，详见博客和商业授权。
