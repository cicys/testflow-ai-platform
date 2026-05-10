# TestFlow Run

当智能体或助手需要创建并执行一次本地 TestFlow 运行时使用本 skill。

## 能力

- 通过公开的 `testflow` CLI 创建 TestFlow 运行。
- 使用 `mock`、`oversee`、`pytest`、`subprocess`、`api_suite` 或 `agent_gateway` 执行运行。
- 输出 Markdown 摘要，包含运行 id、状态、执行器与产物路径。

## 示例

```bash
python3 scripts/run_testflow.py --executor mock
```

命令类执行（oversee）示例：

```bash
python3 scripts/run_testflow.py \
  --executor oversee \
  --config-json '{"command":["python3","-c","print(\"ok\")"]}'
```

HTTP 套件（api_suite）示例：

```bash
python3 scripts/run_testflow.py \
  --executor api_suite \
  --config-json '{"suite_file":"examples/api_suites/http-smoke.json"}'
```

## 说明

- 复杂测试逻辑应放在本 skill 之外，通过 JSON 将配置传给 TestFlow。
- 勿在 `--config-json` 中放置密钥；请使用环境变量或密钥管理服务。
