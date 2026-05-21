# TestFlow AI Platform

TestFlow AI Platform 是一套轻量级的运行台账（run ledger）与执行器框架，面向 AI 辅助的测试与评估工作流。

本仓库提供小而稳的本地优先能力，包括：

- 创建可复现的测试与评估运行。
- 按固定布局写入运行产物（artifacts）。
- 使用 `mock` 执行器做无外部依赖的冒烟验证。
- 使用 `oversee`、`pytest` 或 `subprocess` 执行基于命令的检查。
- 使用 **`api_suite`** 执行 JSON 描述的 HTTP 接口套件。
- 使用 **`ui_suite`** 校验浏览器 UI 套件并生成 Playwright spec。
- 使用 **`agent_gateway`** 调用对话式自动化服务端点。
- 对比运行摘要与样本级预测（predictions）。
- 通过会话、用例批次、覆盖校验与执行进度，管理偏「技能化」的测试工作流。
- 使用 `workflow.json` 跟踪从需求分析到执行、报告、发布检查的项目流程。
- 将 workflow 步骤与 run ledger 关联，支持执行后自动同步步骤状态。
- 通过 JSONL stdio **Tool Server** 将 toolkit 能力暴露给本地 agent 或脚本。
- 从运行或工具集会话生成 **Markdown 报告**。
- 通过 **`toolkit caseops`** 构造或提交通用 CaseOps 载荷（端点由环境变量配置）。
- 通过小型 skill 封装，由助手或智能体运行时触发运行。

## 状态

当前为早期公开预览阶段；核心台账与多种执行器、报告能力已可本地运行。

## 安装

```bash
python3 -m pip install -e ".[dev]"
```

## 快速开始

```bash
export TESTFLOW_HOME="$(pwd)/.testflow"
testflow init

RUN_A=$(testflow run create --executor mock --dataset-version smoke-v1)
testflow run execute "$RUN_A"

RUN_B=$(testflow run create \
  --executor oversee \
  --config-file examples/configs/oversee-smoke.json)
testflow run execute "$RUN_B"

testflow run diff "$RUN_A" "$RUN_A" --sample-key sample_id
```

HTTP API 套件校验与执行：

```bash
testflow api validate-suite examples/api_suites/http-smoke.json

RUN_C=$(testflow run create \
  --executor api_suite \
  --config-json '{"suite_file":"examples/api_suites/http-smoke.json"}')
testflow run execute "$RUN_C"
```

浏览器 UI 套件校验与编译：

```bash
testflow ui validate-suite examples/ui_suites/browser-smoke.json
testflow ui compile-suite examples/ui_suites/browser-smoke.json --output /tmp/browser-smoke.spec.ts

RUN_D=$(testflow run create \
  --executor ui_suite \
  --config-json '{"suite_file":"examples/ui_suites/browser-smoke.json"}')
testflow run execute "$RUN_D"
```

技能工具集与报告：

```bash
testflow toolkit list
testflow toolkit list --domain reporting
testflow toolkit session create demo-project
testflow toolkit case merge-batches <session_id>
testflow toolkit case validate <session_id>
testflow toolkit case init-registry <session_id>
testflow toolkit case update-status <session_id> TC-BIZ-001 passed --executor oversee
testflow toolkit case progress <session_id>
testflow toolkit workflow start demo-project --routes api,ui
testflow toolkit workflow next <session_id>
testflow toolkit workflow complete <session_id> requirement_analysis --summary "Scope captured"
testflow toolkit workflow create-run <session_id> api_suite_execution --executor mock

testflow report run "$RUN_A"
testflow report session <session_id>
```

Tool Server 预览：

```bash
printf '%s\n' \
  '{"id":1,"method":"server.info"}' \
  '{"id":2,"method":"tools.list","params":{"domain":"workflow"}}' \
  '{"id":3,"method":"server.shutdown"}' \
  | testflow server stdio
```

产物写入路径示例：

```text
.testflow/
  registry.sqlite3
  artifacts/
    runs/
      <run_id>/
        manifest.json
        predictions.jsonl
        summary.json
        logs/
```

## CLI（节选）

```bash
testflow init
testflow run create --executor mock
testflow run create --executor oversee --config-file examples/configs/oversee-smoke.json
testflow run create --executor api_suite --config-json '{"suite_file":"examples/api_suites/http-smoke.json"}'
testflow run execute <run_id>
testflow run diff <run_a> <run_b>
testflow dataset register-version smoke-v1 --label "Smoke dataset"

testflow api validate-suite examples/api_suites/http-smoke.json
testflow api run-suite examples/api_suites/http-smoke.json
testflow ui validate-suite examples/ui_suites/browser-smoke.json
testflow ui plan-suite examples/ui_suites/browser-smoke.json
testflow ui compile-suite examples/ui_suites/browser-smoke.json --output /tmp/browser-smoke.spec.ts

testflow report run <run_id>
testflow report artifacts .testflow/artifacts/runs/<run_id>
testflow report session <session_id>
testflow server stdio

testflow toolkit list
testflow toolkit workflow start demo-project --routes api,ui
testflow toolkit workflow status <session_id>
testflow toolkit workflow next <session_id>
testflow toolkit workflow complete <session_id> <step_id> --summary "Done"
testflow toolkit workflow create-run <session_id> <step_id> --executor mock
testflow toolkit workflow sync-run <session_id> <step_id> <run_id>
testflow toolkit workflow record-artifact <session_id> <step_id> suite suite.json --kind suite
testflow toolkit caseops payload --owner tester --project-id sprint-1 --description "smoke ok" --status passed
```

## 执行器

| 执行器 | 用途 |
|---|---|
| `mock` | 无外部依赖的冒烟执行器，输出确定性预测。 |
| `oversee` | 基于命令的监控/检查执行器，适合脚本、pytest 或其他本地命令。 |
| `pytest` | 上述命令执行器的别名。 |
| `subprocess` | 通用子进程命令执行模式。 |
| `api_suite` | 执行 JSON 定义的 HTTP 套件，按 case 写入预测与详细报告。 |
| `ui_suite` | 校验 JSON 定义的浏览器 UI 套件，生成计划与 Playwright spec。 |
| `agent_gateway` | 调用对话式自动化服务，将响应写入产物。 |

`oversee` 配置示例：

```json
{
  "command": ["python3", "-c", "print('ok from Oversee smoke check')"],
  "timeout_seconds": 60
}
```

`agent_gateway` 配置示例：

```json
{
  "base_url": "http://localhost:8080",
  "endpoint": "/chat/sync",
  "message": "执行冒烟检查",
  "timeout_seconds": 120
}
```

`api_suite` 配置示例：

```json
{
  "suite_file": "examples/api_suites/http-smoke.json",
  "timeout_seconds": 30
}
```

`ui_suite` 配置示例：

```json
{
  "suite_file": "examples/ui_suites/browser-smoke.json"
}
```

若提供 `junit_xml`，TestFlow 会将测试用例映射到 `predictions.jsonl`；否则 oversee/subprocess 路径可写入命令级预测。

## 助手 Skill

`skills/testflow-run/` 中的封装可触发一次运行并打印 Markdown 摘要。

```bash
cd skills/testflow-run
python3 scripts/run_testflow.py --executor mock
```

## 文档

- [架构说明](docs/architecture.md)
- [API 套件](docs/api-suite.md)
- [UI 套件](docs/ui-suite.md)
- [报告](docs/reporting.md)
- [Workflow 编排](docs/workflow.md)
- [Tool Server](docs/tool-server.md)
- [Skill Toolkit](docs/skill-toolkit.md)
- [QA 适配（Agent Gateway / CaseOps）](docs/qa-adapters.md)
- [路线图](docs/roadmap.md)
- [公开发布检查清单](docs/release-checklist.md)
- [产品概览](docs/overview-product-zh.md)
- [可行性摘要](docs/feasibility-summary-zh.md)

## 隐私说明

本公开预览刻意保持厂商中立：不包含私有项目名、私有 URL、内部规划笔记或组织专属部署说明。

## 许可证

MIT License，详见 `LICENSE`。
