from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import ClientError

from app.core.aws.s3_client import S3Client
from tests.unit.test_data.s3.build_s3 import ENDPOINT_URL


class TestS3Client:
    @pytest.mark.usefixtures("initialize_s3")
    def test_init(self) -> None:
        s3_client = S3Client()

        assert s3_client.client.meta.endpoint_url == ENDPOINT_URL

    @pytest.mark.usefixtures("initialize_s3")
    def test_get_object(self) -> None:
        s3_client = S3Client()

        content = s3_client.get_object(bucket_name="weights", key="scrfd/Readme.md")

        assert content.startswith(b"# SCRFD weight")

    @pytest.mark.usefixtures("initialize_s3")
    def test_get_object_with_missing_key(self) -> None:
        s3_client = S3Client()

        with pytest.raises(ClientError) as exc_info:
            s3_client.get_object(bucket_name="weights", key="missing-object")

        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    @pytest.mark.usefixtures("initialize_s3")
    def test_get_menu_image(self) -> None:
        """動作確認用メニュー画像をS3から取得できることを確認する。"""
        s3_client = S3Client()

        content = s3_client.get_object(
            bucket_name="menus",
            key="test/test_menu.png",
        )

        assert content.startswith(b"\x89PNG\r\n\x1a\n")

    @pytest.mark.usefixtures("initialize_s3")
    def test_upload_object(self) -> None:
        s3_client = S3Client()
        content = b"%PDF-1.4\nupload test\n"
        file_name = "uploads/test_upload_object.pdf"

        uploaded_file_name = s3_client.upload_object(
            bucket_name="faces",
            file=BytesIO(content),
            file_name=file_name,
        )
        response = s3_client.client.get_object(Bucket="faces", Key=file_name)

        assert uploaded_file_name == file_name
        assert response["Body"].read() == content
        assert response["ContentType"] == "application/pdf"

    @pytest.mark.usefixtures("initialize_s3")
    def test_upload_object_with_content_type(self) -> None:
        """指定したContent-TypeでS3へオブジェクトを登録することを確認する。"""
        s3_client = S3Client()
        content = b"png-image"
        file_name = "101/10.png"

        uploaded_file_name = s3_client.upload_object(
            bucket_name="menus",
            file=BytesIO(content),
            file_name=file_name,
            content_type="image/png",
        )
        response = s3_client.client.get_object(Bucket="menus", Key=file_name)

        assert uploaded_file_name == file_name
        assert response["Body"].read() == content
        assert response["ContentType"] == "image/png"

    @pytest.mark.usefixtures("initialize_s3")
    def test_upload_object_with_missing_bucket(self) -> None:
        s3_client = S3Client()

        with pytest.raises(ClientError) as exc_info:
            s3_client.upload_object(
                bucket_name="missing-bucket",
                file=BytesIO(b"upload test"),
                file_name="uploads/missing_bucket.pdf",
            )

        assert exc_info.value.response["Error"]["Code"] == "NoSuchBucket"

    @pytest.mark.usefixtures("initialize_s3")
    def test_generate_presigned_get_url(self) -> None:
        """指定したS3オブジェクトの署名付きGET URLを生成することを確認する。"""
        s3_client = S3Client()

        result = s3_client.generate_presigned_get_url(
            bucket_name="menus",
            file_name="101/10.png",
            expires_in=3600,
        )
        parsed_url = urlparse(result)
        query = parse_qs(parsed_url.query)

        assert result.startswith(f"{ENDPOINT_URL}/menus/101/10.png?")
        assert "Signature" in query
        assert "Expires" in query

    @pytest.mark.usefixtures("initialize_s3")
    def test_delete_object(self) -> None:
        s3_client = S3Client()
        file_name = "101.png"

        result = s3_client.delete_object(bucket_name="faces", file_name=file_name)

        assert result is None
        with pytest.raises(ClientError) as exc_info:
            s3_client.client.get_object(Bucket="faces", Key=file_name)

        assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    @pytest.mark.usefixtures("initialize_s3")
    def test_delete_object_with_missing_bucket(self) -> None:
        s3_client = S3Client()

        with pytest.raises(ClientError) as exc_info:
            s3_client.delete_object(
                bucket_name="missing-bucket",
                file_name="uploads/missing_bucket.pdf",
            )

        assert exc_info.value.response["Error"]["Code"] == "NoSuchBucket"
