from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


DEFAULT_REGION = os.getenv("AWS_REGION", "ap-northeast-1")
DEFAULT_ENDPOINT_URL = os.getenv("SECRETS_MANAGER_ENDPOINT", "http://localhost:4566")
DEFAULT_SECRET_FILE = Path(__file__).resolve().parent / "secret.json"


def load_secret_string(secret_file: Path) -> str:
    with secret_file.open("r", encoding="utf-8") as file:
        secret_payload = json.load(file)
    return json.dumps(secret_payload, ensure_ascii=False)


def upsert_secret(secret_name: str, secret_string: str, endpoint_url: str, region_name: str) -> None:
    client = boto3.client(
        "secretsmanager",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "dummy"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "dummy"),
    )

    try:
        client.describe_secret(SecretId=secret_name)
        client.put_secret_value(SecretId=secret_name, SecretString=secret_string)
        print(f"Updated secret: {secret_name}")
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        client.create_secret(Name=secret_name, SecretString=secret_string)
        print(f"Created secret: {secret_name}")


def main() -> None:
    secret_file = Path(os.getenv("SECRET_FILE", DEFAULT_SECRET_FILE))
    secret_name = os.getenv("SECRET_NAME", secret_file.stem)

    if not secret_file.exists():
        raise FileNotFoundError(f"Secret file not found: {secret_file}")

    secret_string = load_secret_string(secret_file)
    upsert_secret(
        secret_name=secret_name,
        secret_string=secret_string,
        endpoint_url=os.getenv("SECRETS_MANAGER_ENDPOINT", DEFAULT_ENDPOINT_URL),
        region_name=DEFAULT_REGION,
    )


if __name__ == "__main__":
    main()
