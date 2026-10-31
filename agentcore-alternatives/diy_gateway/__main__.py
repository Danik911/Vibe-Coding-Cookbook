"""Runs the gateway on the laptop: `uv run -m diy_gateway --config gateway.demo.yaml`."""

from __future__ import annotations

import argparse
import logging

import uvicorn

from diy_gateway.app import build_gateway, build_http_app
from diy_gateway.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP tool gateway")
    parser.add_argument("--config", default="gateway.demo.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8210)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    config = load_config(args.config)
    uvicorn.run(build_http_app(build_gateway(config)), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
