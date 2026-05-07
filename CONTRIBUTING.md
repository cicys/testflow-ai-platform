# 贡献指南

感谢你对 TestFlow AI Platform 的贡献。

## 开发环境

```bash
python3 -m pip install -e ".[dev]"
pytest -q
```

## Pull Request 约定

- 变更聚焦、尽量小而清晰。
- 行为变更请新增或更新测试。
- 公开文档保持厂商中立表述。
- 不要提交私有 URL、令牌或内部路径。

## 代码风格

```bash
ruff check src tests
```

## 报告问题时请附上

- 复现步骤
- 期望行为与实际行为
- 环境信息（操作系统、Python 版本）
