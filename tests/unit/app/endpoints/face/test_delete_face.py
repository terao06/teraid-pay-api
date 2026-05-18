from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.postgres.face_embedding import FaceEmbedding


class TestDeleteFace:
    """delete_face エンドポイントの単体テスト。"""

    @patch("app.endpoints.face.faceController.delete_face")
    def test_delete_face_returns_wrapped_success(
        self,
        mock_delete_face,
        client,
    ) -> None:
        """controller の成功結果を success ラップで返すことを確認する。"""
        mock_delete_face.return_value = None

        response = client.request(
            "DELETE",
            "/face/",
            json={
                "user_id": 101,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }
        mock_delete_face.assert_called_once()
        request = mock_delete_face.call_args.kwargs["request"]
        assert request.user_id == 101

    @patch("app.endpoints.face.faceController.delete_face")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (400, "face is not registered"),
            (404, "user not found"),
            (500, "server error"),
        ],
    )
    def test_delete_face_returns_http_exception_from_controller(
        self,
        mock_delete_face,
        status_code,
        message,
        client,
    ) -> None:
        """controller の HTTPException をそのまま返すことを確認する。"""
        mock_delete_face.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.request(
            "DELETE",
            "/face/",
            json={
                "user_id": 101,
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
        """DB 連携で顔特徴量が論理削除されることを確認する。"""
        user_id = 109

        before_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == user_id)
            .one()
        )
        assert before_face_embedding.is_active is True

        response = client_with_db.request(
            "DELETE",
            "/face/",
            json={
                "user_id": user_id,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": None,
        }

        postgres_session.rollback()
        postgres_session.expire_all()

        after_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == user_id)
            .one_or_none()
        )
        assert after_face_embedding is None
