# TestFlow AI Platform

TestFlow AI Platform is a lightweight run ledger and executor framework for AI-assisted testing workflows.

It provides a small, local-first foundation for:

- Creating reproducible test and evaluation runs.
- Writing run artifacts in a stable layout.
- Running dependency-free smoke checks with `mock`.
- Running command-based checks with `oversee`, `pytest`, or `subprocess`.
- Comparing run summaries and sample-level predictions.
- Triggering runs from an assistant or agent runtime through a small skill wrapper.

## Status

This repository is an early public preview. The current focus is the core run ledger, artifact layout, CLI, and executor interface.

## Install

```bash
python3 -m pip install -e ".[dev]"
```

## Quick Start

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

Artifacts are written to:

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
```

## Executors

| Executor | Purpose |
|---|---|
| `mock` | Dependency-free smoke executor that emits deterministic predictions. |
| `oversee` | Command-based monitoring/check executor for scripts, pytest, or other local commands. |
| `pytest` | Alias for the command-based executor. |
| `subprocess` | Generic command execution mode. |

`oversee` accepts a JSON config:

```json
{
  "command": ["python3", "-c", "print('ok from Oversee smoke check')"],
  "timeout_seconds": 60
}
```

If `junit_xml` is provided, TestFlow maps test cases into `predictions.jsonl`; otherwise it writes one command-level prediction.

## Assistant Skill

The optional skill wrapper in `skills/testflow-run/` lets an assistant or agent runtime trigger a run and return a Markdown summary.

```bash
cd skills/testflow-run
python3 scripts/run_testflow.py --executor mock
```

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Release Checklist](docs/release-checklist.md)

## Privacy And Sanitization

This public preview is intentionally vendor-neutral. It does not include private project names, private URLs, internal planning notes, or organization-specific deployment instructions.

## License

MIT License. See `LICENSE`.
