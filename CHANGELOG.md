# 变更日志

## 0.2.0 - API 套件、Agent Gateway、报告与 CaseOps

- 同步 `public-release`：`api_suite`、`agent_gateway` 执行器，`api_testing` 套件运行器。
- 新增 Markdown 报告：`testflow report run|artifacts|session`；工具集 `reporting` 领域。
- 新增 CaseOps 工具命令：`testflow toolkit caseops payload|submit`（环境变量配置端点）。
- 补充示例 `examples/api_suites/`、`examples/configs/api-suite-smoke.json`。
- 新增中文文档：`docs/api-suite.md`、`docs/reporting.md`、`docs/qa-adapters.md`。
- 测试扩展：`test_api_suite`、`test_reports`、`test_caseops_and_agent_gateway`。

## 0.1.2 - 文档措辞

- 统一调整 README、架构文档与摘要类文档中的备注用语，使之更中性。

## 0.1.1 - Skill Toolkit 与文档同步

- 同步公开预览中的 Skill Toolkit：`testflow toolkit` 会话、用例批次合并、覆盖校验与执行进度台账。
- 新增文档 `docs/skill-toolkit.md`；架构文档补充工具集层级说明。
- 仓库内 Markdown 文档统一提供简体中文版本。

## 0.1.0 - 初次公开预览

- 引入基于 SQLite 的运行台账与产物目录布局。
- 提供 CLI 工作流（`testflow init/run/diff`）。
- 提供 mock 与基于命令的执行器。
- 支持样本级 diff。
- 提供助手 skill 封装示例。
- 补充发布文档与公开发布检查清单。
