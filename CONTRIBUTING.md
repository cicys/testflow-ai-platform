# Contributing

Thanks for contributing to TestFlow AI.

## Development Setup

```bash
python3 -m pip install -e ".[dev]"
pytest -q
```

## Pull Request Guidelines

- Keep changes focused and small.
- Add or update tests for behavior changes.
- Keep public docs vendor-neutral.
- Do not include private URLs, tokens, or internal paths.

## Code Style

```bash
ruff check src tests
```

## Issue Reports

Please include:

- Reproduction steps
- Expected vs actual behavior
- Environment details (OS, Python version)
