import boto3
import os
from botocore.exceptions import ClientError


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

    def upload_object(self, bucket_name: str, file: object, filename: str):
        """
        ファイルをS3にアップロード
        
        Args:
            bucket_name: bucket名
            file: アップロード対象ファイルオブジェクト
            filename: ファイル名
        
        Returns:
            str: S3内のファイルパス
        """
        try:
            self.client.upload_fileobj(
                file,
                bucket_name,
                filename,
                ExtraArgs={'ContentType': 'application/pdf'}
            )
            return filename
        except ClientError as e:
            print(f"Error uploading file: {e}")
            raise
