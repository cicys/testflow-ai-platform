# 报告（Markdown）

报告层将 TestFlow 产物转为 Markdown，便于本地查看、挂载到 CI 日志或通过其他集成发布。

只读取公开的产物格式：

- `summary.json`
- `predictions.jsonl`
- `logs/`
- 工具集会话中的 `case_registry.json`

## 运行报告

```bash
testflow report run <run_id>
testflow report artifacts .testflow/artifacts/runs/<run_id>
```

默认输出：

```text
.testflow/artifacts/runs/<run_id>/report.md
```

报告通常包含：执行状态与通过率、执行器与数据集引用、指标表、失败样本列表、相关日志引用。

## 会话报告

```bash
testflow report session <session_id>
```

默认输出：

```text
<TESTFLOW_HOME>/toolkit_sessions/<session_id>/test_report.md
```

包含：用例执行进度、状态分布、失败或阻塞用例、会话产物列表。

## 工具集入口

```bash
testflow toolkit list --domain reporting
```

可用工具：`build_session_report`、`build_run_artifact_report`。
