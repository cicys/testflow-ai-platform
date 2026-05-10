# QA 适配层（Agent Gateway / CaseOps）

该层将「对话式自动化服务」与「用例/CI 平台」接入 TestFlow，且不绑定具体私有系统命名。

## 公开命名

| 名称 | 含义 |
|---|---|
| Agent Gateway | 提供 `/chat` 或 `/chat/sync` 等兼容端点的对话式自动化服务 |
| CaseOps | 通用抽象：管理用例、执行状态与自动化元数据的测试/CI 平台 |

## Agent Gateway 执行器

当外部自动化服务暴露同步对话接口时使用 `agent_gateway`：

```bash
RUN=$(testflow run create \
  --executor agent_gateway \
  --config-json '{
    "base_url": "http://localhost:8080",
    "endpoint": "/chat/sync",
    "message": "为登录服务生成 API 冒烟测试"
  }')
testflow run execute "$RUN"
```

产物示例：`predictions.jsonl`、`summary.json`、`logs/agent_gateway.response.json`、`logs/agent_gateway.error.log`。

别名：`agent_gateway`、`qa_gateway`、`chat_gateway`。

## CaseOps 适配

先生成载荷（不发送）：

```bash
testflow toolkit caseops payload \
  --owner tester \
  --project-id sprint-1 \
  --description "UI smoke passed" \
  --status passed \
  --execution-method ui_automation
```

提交到兼容端点（需配置环境变量）：

```bash
export TESTFLOW_CASEOPS_URL="https://caseops.example.com"
export TESTFLOW_CASEOPS_TOKEN="..."

testflow toolkit caseops submit \
  --owner tester \
  --project-id sprint-1 \
  --description "API regression passed" \
  --status passed \
  --execution-method api_automation
```

默认提交路径：`/api/cases/automation`（以表单字段 `payload` 承载 JSON）。

## 状态映射（节选）

| 状态 | code |
|---|---:|
| `not_executed` | 0 |
| `passed` | 1 |
| `failed` | 2 |
| `blocked` | 3 |
| `skipped` | 4 |
| `running` | 5 |
| `repaired` | 1 |

## 边界

避免在公开仓库中硬编码私有平台名、内网 URL 与组织账号字段；私有对接请用环境变量与部署侧适配完成。
