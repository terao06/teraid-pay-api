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
)

torch = pytest.importorskip("torch")

TEST_DATA_ROOT = Path(__file__).resolve().parents[3] / "test_data"
FACE_IMAGE_PATH = TEST_DATA_ROOT / "images" / "scrfd" / "one_face.png"


class TestUpdateFace:
    """update_face エンドポイントの単体テスト。"""

    @patch("app.endpoints.face.faceController.update_face")
    def test_update_face_returns_wrapped_success(
        self,
        mock_update_face,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_update_face.return_value = None

        response = client.put(
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
        mock_update_face.assert_called_once()
        request = mock_update_face.call_args.kwargs["request"]
        assert request.user_id == 101
        assert request.content == "base64-encoded-image"
        assert request.extension_type.value == "png"

    @patch("app.endpoints.face.faceController.update_face")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (400, "face not found"),
            (404, "user not found"),
            (409, "face already registered"),
            (409, "face is not registered"),
            (500, "server error"),
        ],
    )
    def test_update_face_returns_http_exception_from_controller(
        self,
        mock_update_face,
        status_code,
        message,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_update_face.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.put(
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

    @pytest.mark.usefixtures(
        "initialize_s3",
        "initialize_ssm",
        "use_local_s3_endpoint",
        "postgres_engine",
        "mysql_engine",
        "insert_users",
        "insert_face_embeddings",
    )
    def test_with_db(
        self,
        client_with_db,
        postgres_session,
    ) -> None:
        """DB 連携で顔画像を更新し、保存内容とレスポンスが一致することを確認する。"""
        user_id = 106
        before_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == user_id)
            .one()
        )
        before_updated_at = before_face_embedding.updated_at

        with patch(
            "app.services.face_service.FaceService._validate_face_embedding"
        ) as mock_validate_face_embedding:
            response = client_with_db.put(
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
        mock_validate_face_embedding.assert_called_once()

        postgres_session.rollback()
        postgres_session.expire_all()

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == user_id)
            .one()
        )
        assert saved_face_embedding.face_embedding_id == before_face_embedding.face_embedding_id
        assert len(saved_face_embedding.embedding) == 512
        assert saved_face_embedding.extension_type.value == "png"
        assert saved_face_embedding.is_active is True
        assert saved_face_embedding.updated_at > before_updated_at

        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        response = s3_client.get_object(Bucket="faces", Key=f"{user_id}.png")
        assert response["Body"].read() != b""
