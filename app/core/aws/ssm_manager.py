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
    menu_image_bucket: str
    category_image_bucket: str
    menu_image_url_expires_in: int

    def __init__(self):
        """SSMクライアントと利用するパラメーターを初期化する。

        Args:
            なし。

        Returns:
            なし。
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
        self.menu_image_bucket = self._get_string_parameter(name="menu_image_bucket")
        self.category_image_bucket = self._get_string_parameter(
            name="category_image_bucket"
        )
        self.menu_image_url_expires_in = self._get_integer_parameter(
            name="menu_image_url_expires_in"
        )

    def _get_parameter(self, name: str, with_decryption: bool = True) -> Union[str, Dict[str, Any]]:
        """指定されたパラメーターを取得し、JSON形式の場合は辞書へ変換する。

        Args:
            name: 取得するSSMパラメーター名。
            with_decryption: SecureStringを復号して取得するか。

        Returns:
            文字列またはJSONから変換した辞書。
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
        """指定されたSSMパラメーターを文字列として取得する。

        Args:
            name: 取得するSSMパラメーター名。
            with_decryption: SecureStringを復号して取得するか。

        Returns:
            文字列のパラメーター値。
        """
        value = self._get_parameter(name=name, with_decryption=with_decryption)
        if not isinstance(value, str):
            raise ValueError(f"SSM parameter '{name}' must be a string.")

        return value

    def _get_integer_parameter(self, name: str, with_decryption: bool = True) -> int:
        """指定されたSSMパラメーターを整数として取得する。

        Args:
            name: 取得するSSMパラメーター名。
            with_decryption: SecureStringを復号して取得するか。

        Returns:
            整数のパラメーター値。
        """
        value = self._get_parameter(name=name, with_decryption=with_decryption)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"SSM parameter '{name}' must be an integer.")

        return value
