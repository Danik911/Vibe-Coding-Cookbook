"""Starts the local demo: the app stand-in (8200), the context layer stand-in (8206) and the
gateway (8210), each in its own process. Ctrl+C stops all three. Works on Windows and macOS.

Run: uv run --env-file .env examples/run_demo.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx2

ROOT = Path(__file__).resolve().parents[1]
SERVICES = [
    (
        "app",
        [sys.executable, "-m", "uvicorn", "examples.demo_upstreams.app:app", "--port", "8200"],
        "http://127.0.0.1:8200/api/health",
    ),
    ("context", [sys.executable, "-m", "examples.demo_upstreams.context_server"], None),
    (
        "gateway",
        [sys.executable, "-m", "diy_gateway", "--config", "gateway.demo.yaml", "--port", "8210"],
        "http://127.0.0.1:8210/health",
    ),
]


def wait_for(url: str, seconds: float = 20) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx2.get(url, timeout=1).is_success:
                return
        except httpx2.TransportError:
            pass
        time.sleep(0.3)
    raise SystemExit(f"{url} did not come up")


def main() -> None:
    missing = [key for key in ("GATEWAY_CLAIM_AGENT_KEY", "DEMO_APP_API_KEY") if not os.environ.get(key)]
    if missing:
        raise SystemExit(f"Missing {', '.join(missing)}: run `uv run examples/make_env.py`, then use --env-file .env")
    processes: list[subprocess.Popen] = []
    try:
        for name, command, health in SERVICES:
            processes.append(subprocess.Popen(command, cwd=ROOT))  # noqa: S603 - fixed commands
            if health:
                wait_for(health)
            else:
                time.sleep(2)
            print(f"{name} is up")
        print("Gateway at http://127.0.0.1:8210/mcp. Try: uv run --env-file .env examples/call_gateway.py")
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
