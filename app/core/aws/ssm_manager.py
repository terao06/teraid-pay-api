import boto3
import json
import os
from botocore.exceptions import ClientError
from typing import Union, Dict, Any


class SsmClient:
    s3_endpoint: str
    llm_weight_bucket: str
    adaface_weight: str
    scrfd_weight: str
    face_image_bucket: str

    def __init__(self):
        """
        SSM クライアントの初期化
        """
        self.region_name = os.getenv("AWS_REGION", "ap-northeast-1")
        self.endpoint_url = os.getenv("SSM_ENDPOINT", "http://localstack:4566")

        self.client = boto3.client(
            service_name='ssm',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url
        )

        self.s3_endpoint = self._get_string_parameter(name="s3_endpoint")
        self.llm_weight_bucket = self._get_string_parameter(name="llm_weight_bucket")
        self.adaface_weight = self._get_string_parameter(name="adaface_weight")
        self.scrfd_weight = self._get_string_parameter(name="scrfd_weight")
        self.face_image_bucket = self._get_string_parameter(name="face_image_bucket")

    def _get_parameter(self, name: str, with_decryption: bool = True) -> Union[str, Dict[str, Any]]:
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

    def _get_string_parameter(self, name: str, with_decryption: bool = True) -> str:
        value = self._get_parameter(name=name, with_decryption=with_decryption)
        if not isinstance(value, str):
            raise ValueError(f"SSM parameter '{name}' must be a string.")

        return value
