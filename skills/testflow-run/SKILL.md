# TestFlow Run

Use this skill when an agent or assistant should create and execute a local TestFlow run.

## Capabilities

- Creates a TestFlow run through the public `testflow` CLI.
- Executes the run with `mock`, `oversee`, `pytest`, or `subprocess`.
- Prints a Markdown summary with the run id, status, executor, and artifact path.

## Examples

```bash
python3 scripts/run_testflow.py --executor mock
```

Oversee-style command execution:

```bash
python3 scripts/run_testflow.py \
  --executor oversee \
  --config-json '{"command":["python3","-c","print(\"ok\")"]}'
```

## Notes

- Keep complex test logic outside this skill. Pass configuration to TestFlow as JSON.
- Do not place secrets in `--config-json`; use environment variables or your secret manager.
