# Tool Server

Tool Server 提供一个无额外依赖的 JSONL stdio 适配层，用于把 TestFlow Toolkit 暴露给本地 agent、脚本或自动化运行时。

当前协议是轻量预览版，目标是稳定工具调用边界；后续可在同一工具注册表之上扩展标准 MCP server。

## 启动

```bash
testflow server stdio
```

服务从 `stdin` 读取一行一个 JSON 请求，并向 `stdout` 写回一行一个 JSON 响应。

## 方法

### `server.info`

```json
{"id":1,"method":"server.info"}
```

返回服务名、协议版本和支持的方法。

### `tools.list`

```json
{"id":2,"method":"tools.list","params":{"domain":"workflow"}}
```

返回工具列表。`domain` 可选，例如：

- `session`
- `cases`
- `tracking`
- `reporting`
- `ui`
- `workflow`

### `tools.call`

```json
{
  "id": 3,
  "method": "tools.call",
  "params": {
    "name": "start_workflow",
    "arguments": {
      "project_name": "demo-project",
      "routes": "api,ui"
    }
  }
}
```

`arguments` 会按关键字参数传给工具函数。

Workflow 相关工具也可通过同一入口调用，例如创建并关联一次运行：

```json
{
  "id": 4,
  "method": "tools.call",
  "params": {
    "name": "create_linked_run",
    "arguments": {
      "session_id": "demo-project_20260101_000000",
      "step_id": "api_suite_execution",
      "executor_type": "mock"
    }
  }
}
```

常用 workflow 工具包括 `start_workflow`、`get_next_step`、`create_linked_run`、`sync_run_status`、`record_step_artifact`。

### `server.shutdown`

```json
{"id":5,"method":"server.shutdown"}
```

让 stdio 循环退出。

## 示例

```bash
printf '%s\n' \
  '{"id":1,"method":"server.info"}' \
  '{"id":2,"method":"tools.list","params":{"domain":"ui"}}' \
  '{"id":3,"method":"server.shutdown"}' \
  | testflow server stdio
```

## 边界

- 当前协议是 TestFlow JSONL preview，不声明为完整 MCP 实现。
- 工具函数来自 `testflow toolkit list` 使用的同一个 catalog。
- 不应在请求参数中传递密钥；私有凭据应通过环境变量或外部密钥管理传入。
