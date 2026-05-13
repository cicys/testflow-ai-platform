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

阻塞步骤：

```bash
testflow toolkit workflow block <session_id> api_suite_execution \
  --reason "Target service is unavailable"
```

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
