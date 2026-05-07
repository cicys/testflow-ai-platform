# 公开发布检查清单

在向公开 GitHub 仓库推送前，建议逐项自检。

## 源代码

- [ ] 无私有 URL。
- [ ] 无私有项目名。
- [ ] 无内部工作区路径。
- [ ] 无密钥、令牌或凭证。
- [ ] 无生成的运行产物。
- [ ] 无本地 SQLite 数据库。
- [ ] 无缓存目录。

## 文档

- [ ] README 仅使用对外产品语言。
- [ ] 文档描述通用适配器，而非私有迁移计划。
- [ ] 示例可在干净机器上运行。
- [ ] 许可证已由维护者选定。

## 校验命令

```bash
python3 -m pip install -e ".[dev]"
pytest -q

export TESTFLOW_HOME="$(pwd)/.testflow"
testflow init
RUN=$(testflow run create --executor mock)
testflow run execute "$RUN"
testflow run diff "$RUN" "$RUN"
```

## 建议的 Git 命令示例

```bash
cd public-release
git init
git add .
git status
git commit -m "Initial public preview"
```
