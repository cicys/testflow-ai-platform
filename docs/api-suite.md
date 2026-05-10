# API 套件（HTTP）

API 套件层提供体量小、与厂商无关的 HTTP 自动化描述格式，适用于冒烟、服务回归以及仍需本地可执行的生成型接口用例。

## 套件格式

套件包含若干 case，每个 case 包含有序的 HTTP 步骤。

```json
{
  "suite_id": "http-smoke",
  "name": "HTTP smoke suite",
  "base_url": "http://localhost:8080",
  "variables": {
    "project_id": "demo"
  },
  "cases": [
    {
      "case_id": "case-api-001",
      "name": "health and project lookup",
      "steps": [
        {
          "step_id": "health",
          "name": "read health endpoint",
          "method": "GET",
          "endpoint": "/health",
          "assertions": [
            {"kind": "status_code", "expected": 200}
          ]
        }
      ]
    }
  ]
}
```

可在路径、请求头、查询参数与 JSON 正文中使用 `{{变量名}}` 引用变量。

## 断言（Assertions）

| kind | 含义 |
|---|---|
| `status_code` | 比较 HTTP 状态码 |
| `json_path` | 比较或检查 JSON 响应体中的值 |
| `header` | 比较或检查响应头 |
| `body_contains` | 检查原始响应体是否包含文本 |
| `response_time_ms` | 比较耗时（毫秒） |

常用 operator：`equals`、`not_equals`、`contains`、`exists`、`greater_than`、`less_than`。  
JSON 路径可使用紧凑点号语法，例如 `$.data.id`、`$.items[0].name`。

## 变量抽取（Extract）

某一步可将响应中的值写入变量，供后续步骤使用（示例见仓库 `examples/api_suites/http-smoke.json`）。

包含 `authorization`、`token`、`secret`、`password`、`cookie` 等敏感片段的请求头或查询名会在报告中做脱敏处理。

## CLI

```bash
testflow api validate-suite examples/api_suites/http-smoke.json
testflow api run-suite examples/api_suites/http-smoke.json
```

通过台账执行：

```bash
RUN=$(testflow run create \
  --executor api_suite \
  --config-json '{"suite_file":"examples/api_suites/http-smoke.json"}')
testflow run execute "$RUN"
```

产物写入 `predictions.jsonl`、`summary.json`，并在 `logs/api_suite.report.json` 保留详细报告。
