# Prompts Index

来源：飞书 Wiki `prompt` 页面（已整理为可复用模板）。

## engineering/

- `app-from-zero.md`：从 0 到 1 的生产级 MVP 设计与实现
- `codebase-understand-and-refactor.md`：陌生代码库理解与重构
- `senior-debugging.md`：生产问题排查与稳健修复
- `system-design-and-implementation.md`：系统设计 + 最小可运行实现
- `performance-optimization.md`：性能诊断与优化
- `clean-architecture-refactor.md`：整洁架构重构
- `claude-multi-agent-workflow.md`：多代理协作工作流
- `production-ui-component-builder.md`：生产级 UI 组件设计与实现

## rules/

- `coding-constraints.md`：编码行为约束（不猜测、不越界、可验证）

## 使用方式（建议）

1. 先选一个主 Prompt（`engineering/`）。
2. 再拼接 `rules/coding-constraints.md` 作为尾部约束。
3. 若是复杂任务，增加输入上下文：目标、约束、当前代码位置、验收标准。
