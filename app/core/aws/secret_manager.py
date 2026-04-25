import boto3
import json
import os
from botocore.exceptions import ClientError
from typing import Dict, Any, Union


class SecretManager:
    """AWS Secrets Manager からシークレットを取得するクラスです。"""

    def __init__(self):
        """Secrets Manager クライアントを初期化します。
        Args:
            なし: 引数はありません。

        Returns:
            none: 返り値はありません。
        """
        self.region_name = os.getenv("AWS_REGION", "ap-northeast-1")
        self.endpoint_url = os.getenv("SECRETS_MANAGER_ENDPOINT")

        self.client = boto3.client(
            service_name='secretsmanager',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url
        )

    def get_secret(self, secret_name: str) -> Union[Dict[str, Any], str, bytes]:
        """指定したシークレットを取得します。
        Args:
            secret_name: 取得対象のシークレット名です。

        Returns:
            Union: JSON の場合は辞書、それ以外は文字列またはバイナリです。
        """
        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            raise e

        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            try:
                return json.loads(secret)
            except json.JSONDecodeError:
                return secret
        else:
            return get_secret_value_response['SecretBinary']
