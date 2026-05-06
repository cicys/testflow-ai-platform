# Public Release Checklist

Use this checklist before pushing a public GitHub repository.

## Source

- [ ] No private URLs.
- [ ] No private project names.
- [ ] No internal workspace paths.
- [ ] No secrets, tokens, or credentials.
- [ ] No generated run artifacts.
- [ ] No local SQLite databases.
- [ ] No cache directories.

## Documentation

- [ ] README uses public product language only.
- [ ] Docs describe generic adapters, not private migration plans.
- [ ] Examples run on a clean machine.
- [ ] The license is selected by maintainers.

## Validation

```bash
python3 -m pip install -e ".[dev]"
pytest -q

export TESTFLOW_HOME="$(pwd)/.testflow"
testflow init
RUN=$(testflow run create --executor mock)
testflow run execute "$RUN"
testflow run diff "$RUN" "$RUN"
```

## Suggested Git Commands

```bash
cd testflow-ai-platform
git init
git add .
git status
git commit -m "Initial public preview"
```
