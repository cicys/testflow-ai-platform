# TestFlow AI Platform

TestFlow AI Platform 是一套轻量级的运行台账（run ledger）与执行器框架，面向 AI 辅助的测试与评估工作流。

本仓库提供小而稳的本地优先能力，包括：

- 创建可复现的测试与评估运行。
- 按固定布局写入运行产物（artifacts）。
- 使用 `mock` 执行器做无外部依赖的冒烟验证。
- 使用 `oversee`、`pytest` 或 `subprocess` 执行基于命令的检查。
- 对比运行摘要与样本级预测（predictions）。
- 通过会话、用例批次、覆盖校验与用例执行进度，管理偏「技能化」的测试工作流。
- 通过小型 skill 封装，由助手或智能体运行时触发运行。

## 状态

当前为早期公开预览阶段，重心在核心台账、产物布局、CLI 与执行器接口。

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

技能工具集（Skill Toolkit）相关命令：

```bash
testflow toolkit list
testflow toolkit session create demo-project
testflow toolkit case merge-batches <session_id>
testflow toolkit case validate <session_id>
testflow toolkit case init-registry <session_id>
testflow toolkit case update-status <session_id> TC-BIZ-001 passed --executor oversee
testflow toolkit case progress <session_id>
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

## CLI

```bash
testflow init
testflow run create --executor mock
testflow run create --executor oversee --config-file examples/configs/oversee-smoke.json
testflow run execute <run_id>
testflow run diff <run_a> <run_b>
testflow dataset register-version smoke-v1 --label "Smoke dataset"
testflow toolkit list
testflow toolkit session create demo-project
testflow toolkit case merge-batches <session_id>
testflow toolkit case validate <session_id>
testflow toolkit case init-registry <session_id>
testflow toolkit case update-status <session_id> <case_id> passed
```

## 执行器

| 执行器 | 用途 |
|---|---|
| `mock` | 无外部依赖的冒烟执行器，输出确定性预测。 |
| `oversee` | 基于命令的监控/检查执行器，适合脚本、pytest 或其他本地命令。 |
| `pytest` | 上述命令执行器的别名。 |
| `subprocess` | 通用子进程命令执行模式。 |

`oversee` 接受 JSON 配置，例如：

```json
{
  "command": ["python3", "-c", "print('ok from Oversee smoke check')"],
  "timeout_seconds": 60
}
```

若提供 `junit_xml`，TestFlow 会将测试用例映射到 `predictions.jsonl`；否则写入一条命令级预测记录。

## 助手 Skill

`skills/testflow-run/` 中的可选封装让助手或智能体运行时能够触发一次运行并返回 Markdown 摘要。

```bash
cd skills/testflow-run
python3 scripts/run_testflow.py --executor mock
```

## 文档

- [架构说明](docs/architecture.md)
- [Skill Toolkit](docs/skill-toolkit.md)
- [路线图](docs/roadmap.md)
- [公开发布检查清单](docs/release-checklist.md)
- [产品概览](docs/overview-product-zh.md)
- [可行性摘要](docs/feasibility-summary-zh.md)

## 隐私说明

本公开预览刻意保持厂商中立：不包含私有项目名、私有 URL、内部规划笔记或组织专属部署说明。

## 许可证

MIT License，详见 `LICENSE`。
