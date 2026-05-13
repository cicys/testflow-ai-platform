# 路线图

本路线图描述 TestFlow AI 的公开演进方向，不绑定任何私有实现细节。

## 阶段 1：本地核心

- 基于 SQLite 的运行台账。
- 稳定的产物目录布局。
- `mock` 执行器。
- `oversee` 命令执行器。
- 样本级 diff。
- CLI 优先工作流。
- 助手 skill 封装。

## 阶段 2：执行适配

- Skill Toolkit 会话存储。
- 用例批次合并与校验工具。
- 用例执行注册表与进度跟踪。
- 本地 workflow 编排，用于规划、执行与报告状态推进。
- API 套件运行器与 HTTP 执行适配。
- UI 套件 schema 与 Playwright spec 编译。
- Agent Gateway 执行器（对话式自动化服务）。
- CaseOps 适配（用例与 CI/CD 元数据）。
- 面向运行与会话的 Markdown 报告生成。
- JSONL stdio Tool Server，用于本地 agent/runtime 调用 toolkit。
- 批量模型评估适配（规划中）。
- 更丰富的 pytest/JUnit 摄取。
- 重试与超时策略。
- 可配置资源限制。

## 阶段 3：协作

- 可选 API 服务。
- 报告发布适配。
- 标准 MCP server 适配。
- 数据集导入/导出辅助。
- 人工评审与标注适配接口。

## 阶段 4：平台能力

- Web 控制台。
- 多用户权限。
- 远程执行 Worker。
- 可插拔的可观测性集成。
- 定时监控类工作流。

## 预览阶段的非目标

- 不捆绑私有集成。
- 不包含组织专属部署脚本。
- 不硬依赖某一智能体框架。
- 不要求必须接入托管服务。
