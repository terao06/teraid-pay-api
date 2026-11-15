import boto3
import os
from botocore.exceptions import ClientError


LOCAL_BROWSER_S3_ENDPOINT = "http://localhost:9002"


class S3Client:
    def __init__(self, s3_endpoint: str | None = None):
        self.region_name = os.getenv("AWS_REGION", "ap-northeast-1")
        self.endpoint_url = s3_endpoint or os.getenv("S3_ENDPOINT")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        self.client = boto3.client(
            service_name='s3',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    def get_object(
        self,
        bucket_name: str,
        key: str) -> bytes:

        response = self.client.get_object(Bucket=bucket_name, Key=key)
        return response["Body"].read()

    def upload_object(
        self,
        bucket_name: str,
        file: object,
        file_name: str,
        content_type: str = "application/pdf",
    ):
        """
        ファイルをS3にアップロード
        
        Args:
            bucket_name: bucket名
            file: アップロード対象ファイルオブジェクト
            file_name: ファイル名
            content_type: アップロードするファイルのContent-Type
        
        Returns:
            str: S3内のファイルパス
        """
        try:
            self.client.upload_fileobj(
                file,
                bucket_name,
                file_name,
                ExtraArgs={"ContentType": content_type}
            )
            return file_name
        except ClientError as e:
            print(f"Error uploading file: {e}")
            raise

    def generate_presigned_get_url(
        self,
        bucket_name: str,
        file_name: str,
        expires_in: int,
    ) -> str:
        """S3オブジェクトを取得する署名付きURLを生成する。

        Args:
            bucket_name: bucket名
            file_name: ファイル名（S3キー）
            expires_in: URLの有効期限（秒）

        Returns:
            str: 署名付きGET URL
        """
        presign_client = self.client
        environment = os.getenv("ENV", "local").lower()
        if environment == "local":
            presign_client = boto3.client(
                service_name="s3",
                region_name=self.region_name,
                endpoint_url=LOCAL_BROWSER_S3_ENDPOINT,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )

        return presign_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": file_name},
            ExpiresIn=expires_in,
        )

    def delete_object(self, bucket_name: str, file_name: str) -> None:
        """
        S3のファイルを削除

        Args:
            bucket_name: bucket名
            file_name: ファイル名（S3キー）

        Returns:
            None
        """
        try:
            self.client.delete_object(
                Bucket=bucket_name,
                Key=file_name
            )

        except ClientError as e:
            print(f"Error deleting file: {e}")
            raise
