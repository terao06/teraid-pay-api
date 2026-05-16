import boto3
import json
import os
from botocore.exceptions import ClientError
from typing import Union, Dict, Any


class SsmClient:
    def __init__(self):
        """
        SSM クライアントの初期化
        """
        self.region_name = os.getenv("AWS_REGION", "ap-northeast-1")
        self.endpoint_url = os.getenv("SSM_ENDPOINT")

        self.client = boto3.client(
            service_name='ssm',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url
        )

    def get_parameter(self, name: str, with_decryption: bool = True) -> Union[str, Dict[str, Any]]:
        """
        指定されたパラメータ名で値を取得する。
        JSON形式の場合は辞書型にパースして返す。
        """
        try:
            response = self.client.get_parameter(
                Name=name,
                WithDecryption=with_decryption
            )
            value = response['Parameter']['Value']
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except ClientError as e:
            raise e
