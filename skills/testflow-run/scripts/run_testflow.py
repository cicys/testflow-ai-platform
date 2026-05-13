from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    args = parse_args()
    release_dir = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env.setdefault("TESTFLOW_HOME", str(release_dir / ".testflow"))
    env["PYTHONPATH"] = str(release_dir / "src") + os.pathsep + env.get("PYTHONPATH", "")

    run_cmd([sys.executable, "-m", "testflow_ai.cli", "init"], cwd=release_dir, env=env)

    create_cmd = [
        sys.executable,
        "-m",
        "testflow_ai.cli",
        "run",
        "create",
        "--executor",
        args.executor,
    ]
    if args.dataset_version:
        create_cmd.extend(["--dataset-version", args.dataset_version])
    if args.config_json:
        create_cmd.extend(["--config-json", args.config_json])
    run_id = run_cmd(create_cmd, cwd=release_dir, env=env).stdout.strip().splitlines()[-1]

    execute = run_cmd(
        [sys.executable, "-m", "testflow_ai.cli", "run", "execute", run_id],
        cwd=release_dir,
        env=env,
    )
    summary = json.loads(execute.stdout)
    artifact_root = Path(env["TESTFLOW_HOME"]) / "artifacts" / "runs" / run_id

    print(f"### TestFlow Run `{run_id}`")
    print()
    print(f"- status: `{summary.get('status')}`")
    print(f"- executor: `{summary.get('executor_type')}`")
    print(f"- artifact: `{artifact_root}`")
    print()
    print("```json")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("```")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and execute a TestFlow run.")
    parser.add_argument(
        "--executor",
        default="mock",
        help="mock | oversee | pytest | subprocess | api_suite | ui_suite | agent_gateway",
    )
    parser.add_argument("--dataset-version", default="")
    parser.add_argument("--config-json", default="")
    return parser.parse_args()


def run_cmd(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr or proc.stdout or f"command failed: {command}")
    return proc


if __name__ == "__main__":
    main()
