# UI 套件

UI 套件层提供小而中立的浏览器自动化描述格式，用于描述 Web/H5 流程，而不绑定任何私有录制器、设备平台或浏览器执行服务。

当前公开预览支持校验 UI 套件、生成确定性执行计划，并编译 Playwright test spec。`ui_suite` 执行器会把这些生成产物写入 TestFlow 的标准运行目录。真实浏览器执行可以交给 Playwright 本身，也可以在后续接入远程 Worker。

## 套件格式

```json
{
  "suite_id": "browser-smoke",
  "name": "Browser smoke suite",
  "base_url": "http://localhost:3000",
  "browser": "chromium",
  "variables": {
    "email": "tester@example.com"
  },
  "cases": [
    {
      "case_id": "case-ui-001",
      "name": "login dashboard",
      "steps": [
        {
          "step_id": "open-login",
          "name": "open login page",
          "action": "goto",
          "url": "/login"
        }
      ]
    }
  ]
}
```

可在 URL、选择器和值中使用 `{{name}}` 引用变量。

## 动作

| action | 含义 |
|---|---|
| `goto` | 打开 URL。 |
| `click` | 点击选择器。 |
| `fill` | 向选择器输入文本。 |
| `select` | 选择下拉选项。 |
| `check` | 勾选复选框或单选项。 |
| `uncheck` | 取消勾选。 |
| `press` | 在选择器上按键。 |
| `hover` | 悬停到选择器。 |
| `wait_for_selector` | 等待选择器可见。 |
| `wait_for_url` | 等待页面 URL。 |
| `assert_url` | 断言页面 URL。 |
| `assert_text` | 断言选择器包含文本。 |
| `assert_visible` | 断言选择器可见。 |
| `assert_hidden` | 断言选择器隐藏。 |
| `screenshot` | 在生成的 Playwright spec 中截图。 |

## CLI

校验套件：

```bash
testflow ui validate-suite examples/ui_suites/browser-smoke.json
```

生成计划：

```bash
testflow ui plan-suite examples/ui_suites/browser-smoke.json
```

编译 Playwright spec：

```bash
testflow ui compile-suite examples/ui_suites/browser-smoke.json \
  --output /tmp/browser-smoke.spec.ts
```

通过台账创建运行：

```bash
RUN=$(testflow run create \
  --executor ui_suite \
  --config-json '{"suite_file":"examples/ui_suites/browser-smoke.json"}')

testflow run execute "$RUN"
```

执行器写入：

```text
.testflow/artifacts/runs/<run_id>/
  predictions.jsonl
  summary.json
  logs/
    ui_suite.plan.json
    ui_suite.playwright.spec.ts
```

`browser_suite` 是 `ui_suite` 的别名。
