"""ローカルのテスト用SSMへ共通設定を投入する。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import boto3


BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "teraid_pay_api_setting.json"
ENDPOINT_URL = os.getenv("SSM_ENDPOINT", "http://localhost:4566")
REGION_NAME = os.getenv("AWS_REGION", "ap-northeast-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "dummy")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "dummy123")


def load_parameters(settings_file: Path) -> dict[str, str]:
    with settings_file.open(encoding="utf-8") as file:
        settings: dict[str, Any] = json.load(file)

    parameters: dict[str, str] = {}
    for name, value in settings.items():
        if isinstance(value, dict):
            parameters[name] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            continue

        parameters[name] = str(value)

    return parameters


def put_mock_ssm_parameters(settings_file: Path = SETTINGS_FILE) -> dict[str, str]:
    """テスト用SSMに共通設定を投入し、投入した設定を返す。

    Args:
        settings_file: パラメーター名と値を定義したJSONファイル。

    Returns:
        SSMに登録したパラメーター名と文字列値。
    """
    parameters = load_parameters(settings_file)
    ssm_client = boto3.client(
        "ssm",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    for name, value in parameters.items():
        print(f"パラメータストア作成開始 パラメータ名: {name}")
        ssm_client.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True,
        )
    return parameters


def main() -> None:
    put_mock_ssm_parameters()


if __name__ == "__main__":
    main()
