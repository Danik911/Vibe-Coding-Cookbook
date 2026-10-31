"""Loading configs: the demo's and the AWS deployment's."""

from __future__ import annotations

from pathlib import Path

import pytest

from diy_gateway.config import GatewayConfig, PolicyMode, SigV4Credentials, load_config
from diy_gateway.inbound import role_arn

ROOT = Path(__file__).resolve().parents[1]
AWS_SETTINGS = {
    "UNDERCOVER_API": "https://app123.lambda-url.us-east-1.on.aws",
    "UNDERCOVER_CONTEXT": "https://ctx123.lambda-url.us-east-1.on.aws/mcp",
    "APP_KEY_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret:undercover/app-key-AbCdEf",
    "POLICY_STORE_ID": "PSEXAMPLEabcdefg111111",
    "POLICY_MODE": "log_only",
}


@pytest.mark.parametrize("name", ["gateway.demo.yaml", "gateway.undercover.yaml"])
def test_the_shipped_local_configs_load(name: str):
    config = load_config(ROOT / name)
    assert [target.name for target in config.targets] == ["undercover-app", "undercover-context"]
    assert config.resolve_path(str(config.policy.policies_file)).exists()


def test_the_aws_config_takes_its_settings_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    for name, value in AWS_SETTINGS.items():
        monkeypatch.setenv(name, value)
    config = load_config(ROOT / "examples" / "aws_native" / "gateway.aws.yaml")
    app, context = config.targets
    assert app.spec_url == "https://app123.lambda-url.us-east-1.on.aws/api/agent/openapi.json"
    assert app.credentials.secret == f"aws-secretsmanager:{AWS_SETTINGS['APP_KEY_SECRET_ARN']}"
    assert isinstance(context.credentials, SigV4Credentials)
    assert config.policy.mode is PolicyMode.LOG_ONLY


def test_a_missing_setting_is_named(monkeypatch: pytest.MonkeyPatch):
    for name in AWS_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="UNDERCOVER_API"):
        load_config(ROOT / "examples" / "aws_native" / "gateway.aws.yaml")


@pytest.mark.parametrize(
    ("arn", "expected"),
    [
        ("arn:aws:sts::123456789012:assumed-role/agent/session-1", "arn:aws:iam::123456789012:role/agent"),
        ("arn:aws:iam::123456789012:user/ops", "arn:aws:iam::123456789012:user/ops"),
    ],
)
def test_an_assumed_role_session_is_named_by_its_role(arn: str, expected: str):
    assert role_arn(arn) == expected


@pytest.mark.parametrize(
    ("target", "separator"),
    [("undercover_app", "___"), ("app-", "___"), ("app", "-"), ("app", "x")],
)
def test_names_that_could_put_a_tool_under_the_wrong_target_are_refused(
    demo_config: GatewayConfig, target: str, separator: str
):
    data = demo_config.model_dump(mode="json")
    data["targets"][0]["name"] = target
    data["separator"] = separator
    with pytest.raises(ValueError, match="separator|target names"):
        GatewayConfig.model_validate(data)
