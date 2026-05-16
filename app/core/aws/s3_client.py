import boto3
import os
from urllib.parse import urlparse


class S3Client:
    def __init__(self):
        self.region_name = os.getenv("AWS_REGION", "ap-northeast-1")
        self.endpoint_url = os.getenv("S3_ENDPOINT")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        self.client = boto3.client(
            service_name='s3',
            region_name=self.region_name,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )

    def get_objects(
        self,
        bucket_name: str,
        object_paths: list[str]) -> list[bytes]:
        objects = []
        for path in object_paths:
            parsed_url = urlparse(path)
            key = parsed_url.path.lstrip('/')
            
            response = self.client.get_object(Bucket=bucket_name, Key=key)
            objects.append(response['Body'].read())
            
        return objects
