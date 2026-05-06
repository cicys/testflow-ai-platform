# Architecture

TestFlow AI Platform is organized around a small set of stable contracts.

## Layers

```text
Assistant / CLI / API
        |
        v
TestFlow Core
  - Run ledger
  - Artifact layout
  - Diff and summary
  - Executor registry
        |
        v
Executors
  - mock
  - oversee / pytest / subprocess
  - future adapters
```

## Core Concepts

| Concept | Meaning |
|---|---|
| `DatasetVersion` | A reproducible reference to test or evaluation inputs. |
| `Run` | One execution attempt with an executor, config snapshot, status, and artifacts. |
| `Prediction` | Sample-level output written as JSON Lines. |
| `MetricResult` | A named metric attached to a run. |
| `Artifact` | Files written under `.testflow/artifacts/runs/<run_id>/`. |

## Artifact Layout

```text
.testflow/artifacts/runs/<run_id>/
  manifest.json
  predictions.jsonl
  summary.json
  logs/
    executor.stdout.log
    executor.stderr.log
```

`manifest.json` captures the run id, executor type, dataset version, sanitized executor config, and optional trace fields.

`predictions.jsonl` is the sample-level comparison surface. Each row should include:

```json
{"sample_id":"case-001","output":{"label":"ok"},"error":null}
```

`summary.json` is the run-level reporting surface. It should include status, counts, and metrics.

## Executor Contract

Executors receive:

- `run_id`
- `artifact_root`
- `config`

Executors must:

- Write only under `artifact_root`.
- Write `predictions.jsonl` and `summary.json`.
- Return an exit code and summary.
- Never write secrets to the manifest or logs intentionally.

## Built-in Executors

`mock` emits deterministic predictions and is used for smoke testing.

`oversee` runs local commands and maps stdout, stderr, exit code, and optional JUnit XML into TestFlow artifacts. It is intended for monitoring-style checks, scheduled validations, pytest suites, and shell-friendly tools.

## Extension Points

Future adapters can be added without changing the ledger schema:

- API test runners
- UI automation runners
- model evaluation jobs
- batch inference jobs
- remote execution services
- reporting backends
