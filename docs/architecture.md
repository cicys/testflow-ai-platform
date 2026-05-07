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
  - 执行器注册
  - Skill Toolkit 会话
        |
        v
Executors
  - mock
  - oversee / pytest / subprocess
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

执行器接收：

- `run_id`
- `artifact_root`
- `config`

执行器必须：

- 仅在 `artifact_root` 下写入。
- 写入 `predictions.jsonl` 与 `summary.json`。
- 返回退出码与摘要。
- 避免在 manifest 或日志中故意写入密钥。

## 内置执行器

`mock` 输出确定性预测，用于冒烟测试。

`oversee` 在本地执行命令，并将 stdout、stderr、退出码以及可选的 JUnit XML 映射为 TestFlow 产物，适用于监控式检查、定时校验、pytest 套件以及 shell 友好工具。

## 扩展点

未来可在不改动台账模式的前提下增加适配器：

- API 测试运行器
- UI 自动化运行器
- 模型评估任务
- 批量推理任务
- 远程执行服务
- 报告后端

## Skill Toolkit 层

工具集层提供不绑定单次运行的流程能力：

- 会话产物管理。
- 用例批次合并。
- 用例覆盖校验。
- 用例执行注册表与进度跟踪。

这些能力通过 `testflow toolkit ...` 暴露，后续可由 API 服务、助手 skill 或工具服务器封装。
