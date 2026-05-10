# Skill Toolkit

Skill Toolkit 在 TestFlow 运行台账之上提供可复用的流程工具，适用于助手驱动的测试流程：规划、用例生成、执行与报告可能分布在多步完成。

## 目标

- 将工作流产物固定在稳定的会话目录中。
- 合并分批生成的测试用例。
- 在执行前校验用例质量。
- 跨不同执行器跟踪用例级执行状态。
- 通过公开的 `testflow toolkit` CLI 暴露能力。

## 会话布局

工具集会话位于：

```text
.testflow/
  toolkit_sessions/
    <session_id>/
      session.json
      03_test_cases_batch_1.json
      03_test_cases_batch_2.json
      03_test_cases.json
      case_coverage_report.json
      case_registry.json
```

## 工具目录

```bash
testflow toolkit list
```

当前内置工具：

| 工具 | 领域 | 用途 |
|---|---|---|
| `create_session` | session | 创建工具集会话产物目录。 |
| `list_sessions` | session | 列出最近的工具集会话。 |
| `write_artifact` | session | 向会话写入 JSON 或文本产物。 |
| `read_artifact` | session | 从会话读取 JSON 或文本产物。 |
| `merge_case_batches` | cases | 合并 `03_test_cases_batch_N.json` 文件。 |
| `validate_case_coverage` | cases | 校验用例数量、字段、场景平衡与可追溯性。 |
| `init_case_registry` | tracking | 基于用例集合创建 `case_registry.json`。 |
| `update_case_status` | tracking | 更新单条用例状态。 |
| `get_execution_progress` | tracking | 汇报执行与通过率进度。 |
| `build_session_report` | reporting | 基于工具集会话生成 Markdown 报告。 |
| `build_run_artifact_report` | reporting | 基于某次运行的产物目录生成 Markdown 报告。 |

按领域筛选：`testflow toolkit list --domain reporting`。

## 用例批次格式

批次文件命名示例：

```text
03_test_cases_batch_1.json
03_test_cases_batch_2.json
```

每个批次可以是直接用例集合，或由 `test_case_set` 包裹：

```json
{
  "test_case_set": {
    "test_cases": [
      {
        "case_id": "draft-1",
        "title": "Login happy path",
        "test_point_id": "TP-1",
        "strategy": "business",
        "design_technique": "scenario",
        "tag": "positive",
        "requirement_type": "functional",
        "priority": "P1",
        "test_steps": [
          {"step": "Open login page", "expected": "The page is visible"}
        ]
      }
    ]
  }
}
```

合并时会按 `test_point_id + title` 去重、重新编号 case id，并写入 `03_test_cases.json`。

## 用例注册表

`case_registry.json` 使用下列状态：

- `not_executed`
- `running`
- `passed`
- `failed`
- `blocked`
- `skipped`
- `repaired`

示例：

```bash
testflow toolkit case init-registry <session_id>
testflow toolkit case update-status <session_id> TC-BIZ-001 passed --executor oversee
testflow toolkit case progress <session_id>
```

## 公开边界

Skill Toolkit 刻意保持框架中立：不要求特定的助手运行时、工具服务器、浏览器驱动、移动端驱动或协作平台。上述集成可作为适配器叠加，同时保持会话与用例契约稳定。
