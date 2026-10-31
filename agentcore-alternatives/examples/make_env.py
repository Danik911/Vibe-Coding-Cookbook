"""Writes `.env` for the local demo with fresh random keys, without printing them.

Run: uv run examples/make_env.py
"""

from __future__ import annotations

import secrets
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / ".env"
KEYS = ("GATEWAY_CLAIM_AGENT_KEY", "DEMO_APP_API_KEY")


def main() -> None:
    existing = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    present = {line.split("=", 1)[0].strip() for line in existing.splitlines() if "=" in line}
    missing = [key for key in KEYS if key not in present]
    lines = [f"{key}={secrets.token_urlsafe(32)}" for key in missing]
    if lines:
        separator = "" if not existing or existing.endswith("\n") else "\n"
        ENV.write_text(existing + separator + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"{ENV.name}: added {', '.join(missing) or 'nothing'}; values not shown")


if __name__ == "__main__":
    main()
