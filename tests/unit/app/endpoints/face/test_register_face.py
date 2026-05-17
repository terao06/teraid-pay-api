import base64
from pathlib import Path
from unittest.mock import patch

import boto3
from fastapi import HTTPException
import pytest

from app.models.postgres.face_embedding import FaceEmbedding
from tests.unit.test_data.s3.build_s3 import ENDPOINT_URL as S3_ENDPOINT_URL
from tests.unit.test_data.s3.build_s3 import REGION_NAME as S3_REGION_NAME
from tests.unit.test_data.ssm.build_ssm import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    ENDPOINT_URL as SSM_ENDPOINT_URL,
    REGION_NAME as SSM_REGION_NAME,
)

torch = pytest.importorskip("torch")

TEST_DATA_ROOT = Path(__file__).resolve().parents[3] / "test_data"
FACE_IMAGE_PATH = TEST_DATA_ROOT / "images" / "scrfd" / "one_face.png"


class TestRegisterFace:
    """register_face エンドポイントの単体テスト。"""

    @patch("app.endpoints.face.faceController.register_face")
    def test_register_face_returns_wrapped_success(
        self,
        mock_register_face,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_register_face.return_value = None

        response = client.post(
            "/face/",
            json={
                "user_id": 101,
                "content": "base64-encoded-image",
                "extension_type": "png",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_register_face.assert_called_once()
        request = mock_register_face.call_args.kwargs["request"]
        assert request.user_id == 101
        assert request.content == "base64-encoded-image"
        assert request.extension_type.value == "png"

    @patch("app.endpoints.face.faceController.register_face")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (400, "face not found"),
            (409, "face already registered"),
            (500, "server error"),
        ],
    )
    def test_register_face_returns_http_exception_from_controller(
        self,
        mock_register_face,
        status_code,
        message,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_register_face.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.post(
            "/face/",
            json={
                "user_id": 101,
                "content": "base64-encoded-image",
                "extension_type": "png",
            },
        )

        assert response.status_code == status_code
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": message,
            }
        }

    @pytest.mark.usefixtures("postgres_engine", "mysql_engine", "insert_users", "initialize_s3", "initialize_ssm")
    def test_with_db(
        self,
        client_with_mysql_postgres_db,
        postgres_session,
    ) -> None:
        """DB 連携で顔画像を登録し、保存内容とレスポンスが一致することを確認する。"""
        self._put_ssm_parameter("s3_endpoint", S3_ENDPOINT_URL)
        user_id = 101

        response = client_with_mysql_postgres_db.post(
            "/face/",
            json={
                "user_id": user_id,
                "content": base64.b64encode(FACE_IMAGE_PATH.read_bytes()).decode("ascii"),
                "extension_type": "png",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == user_id)
            .one()
        )
        assert saved_face_embedding.face_embedding_id is not None
        assert len(saved_face_embedding.embedding) == 512
        assert saved_face_embedding.is_active is True
        assert saved_face_embedding.created_at is not None
        assert saved_face_embedding.updated_at is not None
        assert saved_face_embedding.deleted_at is None

        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        response = s3_client.get_object(Bucket="faces", Key=f"{user_id}.png")
        assert response["Body"].read() != b""

    @staticmethod
    def _put_ssm_parameter(name: str, value: str) -> None:
        ssm_client = boto3.client(
            "ssm",
            endpoint_url=SSM_ENDPOINT_URL,
            region_name=SSM_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        ssm_client.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True,
        )
