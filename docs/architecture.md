# 架构

TestFlow AI 围绕一组小而稳定的契约组织代码。

## 分层

```text
助手 / CLI / API
        |
        v
TestFlow Core
  - 运行台账
  - 产物布局
  - Diff 与摘要
  - Markdown 报告
  - 执行器注册
  - Skill Toolkit 会话
  - Workflow 状态
  - Tool Server
        |
        v
Executors
  - mock
  - oversee / pytest / subprocess
  - api_suite
  - ui_suite
  - agent_gateway
  - 后续适配器
```

## 核心概念

| 概念 | 含义 |
|---|---|
| `DatasetVersion` | 对测试或评估输入的可复现引用。 |
| `Run` | 一次执行尝试，包含执行器、配置快照、状态与产物。 |
| `Prediction` | 样本级输出，以 JSON Lines 形式写入。 |
| `MetricResult` | 挂载在某个运行上的命名指标。 |
| `Artifact` | 写入 `.testflow/artifacts/runs/<run_id>/` 下的文件。 |
| `ToolkitSession` | 多步规划、用例管理与进度跟踪所用的工作流产物目录。 |

## 产物布局

```text
.testflow/artifacts/runs/<run_id>/
  manifest.json
  predictions.jsonl
  summary.json
  logs/
    executor.stdout.log
    executor.stderr.log
```

`manifest.json` 记录运行 id、执行器类型、数据集版本、不含密钥等敏感字段的执行器配置快照以及可选的追踪字段。

`predictions.jsonl` 是样本级对比面，每行建议包含：

```json
{"sample_id":"case-001","output":{"label":"ok"},"error":null}
```

`summary.json` 是运行级报告面，应包含状态、计数与指标。

## 执行器契约

执行器接收：`run_id`、`artifact_root`、`config`。

执行器必须：仅在 `artifact_root` 下写入；写入 `predictions.jsonl` 与 `summary.json`；返回退出码与摘要；避免在 manifest 或日志中故意写入密钥。

## 内置执行器

`mock` 输出确定性预测，用于冒烟测试。

`oversee` 在本地执行命令，并将 stdout、stderr、退出码以及可选的 JUnit XML 映射为 TestFlow 产物。

`api_suite` 执行 JSON 描述的 HTTP 用例，校验断言、支持步骤间变量抽取，并为每个 API case 写入预测记录。

`ui_suite` 校验 JSON 描述的浏览器 UI 流程，生成确定性执行计划，并编译 Playwright spec。

`agent_gateway` 调用对话式自动化服务，将响应写入预测与日志产物。

## 扩展点

未来可在不改动台账模式的前提下增加适配器：更多 API/UI 运行器、模型评测、批量推理、远程执行、报告发布后端、用例与 CI/CD 平台适配等。

## Skill Toolkit 层

工具集层提供不绑定单次运行的流程能力：会话产物管理、用例批次合并、覆盖校验、执行注册表与进度跟踪。通过 `testflow toolkit ...` 暴露。

## 报告层

报告层读取稳定的产物格式，生成 Markdown 摘要；支持单次运行目录与工具集会话，所有执行器可共用同一报告面，无需绑定私有发布系统。

## Workflow 层

Workflow 层在工具集会话内维护 `workflow.json`，用于记录当前步骤、路由选择、完成摘要、阻塞原因与整体进度。执行类步骤可以关联 run ledger 中的运行记录，并在执行结束后把状态同步回步骤。它为后续 MCP/tool server、多智能体编排或远程执行提供稳定状态机。

## Tool Server 层

Tool Server 层通过 JSONL stdio 协议暴露 toolkit catalog。它不引入额外运行时依赖，适合本地 agent、脚本或未来 MCP 适配器复用同一批工具函数。
