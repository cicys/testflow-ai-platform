# Workflow 编排

Workflow 层用于跟踪一个测试项目从规划到执行、报告的推进状态。它保持本地优先和厂商中立，不要求绑定私有文档平台、聊天工具或项目管理系统。

Workflow 状态存储在工具集会话目录的 `workflow.json` 中。

## 默认步骤

| 步骤 | 用途 |
|---|---|
| `requirement_analysis` | 记录范围、验收标准、风险与待确认问题。 |
| `test_point_analysis` | 将需求拆解为可测试点与覆盖维度。 |
| `test_plan_design` | 定义策略、环境、优先级、准出标准和执行路由。 |
| `case_design` | 创建或导入测试用例并校验覆盖。 |
| `case_registry` | 初始化用例执行跟踪。 |
| `api_suite_preparation` | 准备 API suite 定义。 |
| `api_suite_execution` | 执行 API 检查并收集运行产物。 |
| `ui_suite_preparation` | 准备浏览器 UI suite 定义。 |
| `ui_suite_execution` | 编译或执行浏览器 UI 检查。 |
| `report_generation` | 生成综合 Markdown 报告。 |
| `release_review` | 复核发布门禁和后续动作。 |

路由相关步骤由 `--routes` 控制。

支持的路由别名：

- `api`
- `functional`
- `ui`
- `web`
- `browser`
- `all`

## CLI

创建会话并初始化 workflow：

```bash
testflow toolkit workflow start demo-project --routes api,ui
```

查看进度：

```bash
testflow toolkit workflow status <session_id>
```

启动并返回下一步：

```bash
testflow toolkit workflow next <session_id>
```

完成步骤：

```bash
testflow toolkit workflow complete <session_id> requirement_analysis \
  --summary "Scope captured" \
  --artifact 01_requirement_analysis.json
```

为执行步骤创建并关联一次运行：

```bash
testflow toolkit workflow create-run <session_id> api_suite_execution \
  --executor api_suite \
  --config-json '{"suite_file":"examples/api_suites/http-smoke.json"}'
```

执行完成后，把 run ledger 中的状态同步回 workflow：

```bash
testflow run execute <run_id>
testflow toolkit workflow sync-run <session_id> api_suite_execution <run_id>
```

关联已有运行：

```bash
testflow toolkit workflow link-run <session_id> api_suite_execution <run_id> \
  --executor api_suite \
  --artifact-root .testflow/artifacts/runs/<run_id> \
  --status succeeded
```

记录步骤产物：

```bash
testflow toolkit workflow record-artifact <session_id> api_suite_preparation api-suite api_suite.json \
  --kind suite \
  --summary "API suite is ready"
```

阻塞步骤：

```bash
testflow toolkit workflow block <session_id> api_suite_execution \
  --reason "Target service is unavailable"
```

## 运行关联

`create-run` 会创建标准 TestFlow run、初始化运行产物目录，并在 `workflow.json` 的对应步骤下写入 `runs` 列表。

步骤可以同时记录两类关联信息：

- `runs`：与 run ledger 对应的执行记录，包括 `run_id`、执行器、状态和产物根目录。
- `artifacts`：步骤过程中产生的补充产物，例如 suite 定义、测试计划、截图索引或报告路径。

`sync-run` 会读取本地 run ledger 与 `summary.json`：

- run 成功时，默认将步骤标记为 `completed`。
- run 失败时，默认将步骤标记为 `blocked`。
- 使用 `--no-complete-on-terminal` 可以只同步 run 状态，不推进步骤状态。

## 工具目录

Workflow 工具位于 `workflow` domain：

```bash
testflow toolkit list --domain workflow
```

可用工具：

- `start_workflow`
- `init_workflow`
- `get_workflow_status`
- `get_next_step`
- `complete_step`
- `create_linked_run`
- `link_run`
- `sync_run_status`
- `record_step_artifact`
