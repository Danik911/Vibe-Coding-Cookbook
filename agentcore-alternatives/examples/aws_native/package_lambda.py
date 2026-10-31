"""Builds the gateway's Lambda package, `dist/gateway.zip`, on Windows or macOS.

It installs the project's runtime dependencies (no dev or demo groups) as Linux x86_64
wheels for Python 3.12, at the lockfile's versions, beside the gateway's code, its
policies and its AWS config. Nothing here touches AWS.

Run: uv run examples/aws_native/package_lambda.py
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "gateway.zip"
LAMBDA_ZIP_LIMIT_MB = 50


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603 - fixed commands


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        build = Path(temp) / "package"
        requirements = Path(temp) / "requirements.txt"
        run(
            "uv", "export", "--quiet", "--frozen", "--no-default-groups", "--no-hashes",
            "--no-emit-project", "--format", "requirements-txt", "-o", str(requirements),
        )  # fmt: skip
        run(
            "uv", "pip", "install", "--quiet", "--target", str(build), "-r", str(requirements),
            "--python-platform", "x86_64-manylinux2014", "--python-version", "3.12", "--only-binary", ":all:",
        )  # fmt: skip
        shutil.copytree(ROOT / "diy_gateway", build / "diy_gateway", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "policies", build / "policies")
        shutil.copy(ROOT / "examples" / "aws_native" / "gateway.aws.yaml", build / "gateway.aws.yaml")
        DIST.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(DIST, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(build.rglob("*")):
                if file.is_file() and "__pycache__" not in file.parts:
                    archive.write(file, file.relative_to(build))
    size_mb = DIST.stat().st_size / 1_000_000
    print(f"{DIST.relative_to(ROOT)}: {size_mb:.1f} MB zipped (Lambda's limit is {LAMBDA_ZIP_LIMIT_MB} MB)")
    if size_mb > LAMBDA_ZIP_LIMIT_MB:
        raise SystemExit("The package is over Lambda's limit")


if __name__ == "__main__":
    main()
