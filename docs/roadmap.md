# Roadmap

This roadmap describes the public direction for TestFlow AI Platform without tying the project to any private implementation.

## Phase 1: Local Core

- SQLite-backed run ledger.
- Stable artifact layout.
- `mock` executor.
- `oversee` command executor.
- Sample-level diff.
- CLI-first workflow.
- Assistant skill wrapper.

## Phase 2: Execution Adapters

- HTTP executor adapter.
- Batch model evaluation adapter.
- Richer pytest/JUnit ingestion.
- Retry and timeout policies.
- Configurable resource limits.

## Phase 3: Collaboration

- Optional API service.
- Report generation.
- Dataset import/export helpers.
- Human review and annotation adapter interface.

## Phase 4: Platform Features

- Web dashboard.
- Multi-user permissions.
- Remote execution workers.
- Pluggable observability integrations.
- Scheduled monitoring workflows.

## Non-goals For The Preview

- No bundled private integrations.
- No organization-specific deployment scripts.
- No hard dependency on a specific agent framework.
- No hosted service requirement.
