import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from app.core.exceptions.custom_exception import (
    FaceEmbeddingNotFoundException,
    UserNotFoundException,
)
from app.services.payment_service import PaymentService


class TestGetUserIdFromFaceImage:
    """PaymentService.get_user_id_from_face_image の単体テスト。"""

    def _build_base64_image(self) -> str:
        image = Image.new("RGB", (1, 1), color=(255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_returns_matched_user_id(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
    ) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        threshold = 0.42
        embedding = [0.1, 0.2, 0.3]
        face_info = SimpleNamespace(user_id=123, distance=0.41)
        user = SimpleNamespace(user_id=123)
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")
        s3_client = Mock()

        mock_ssm_client_class.return_value = ssm_params
        mock_s3_client_class.return_value = s3_client
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = face_info
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user

        result = PaymentService().get_user_id_from_face_image(
            mysql_session=mysql_session,
            postgres_session=postgres_session,
            content=content,
            threshold=threshold,
        )

        mock_ssm_client_class.assert_called_once_with()
        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_get_embedding_from_image.assert_called_once()
        embedding_kwargs = mock_get_embedding_from_image.call_args.kwargs
        assert embedding_kwargs["image"].mode == "RGB"
        assert embedding_kwargs["s3_client"] is s3_client
        assert embedding_kwargs["ssm_params"] is ssm_params
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
        )
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=face_info.user_id,
        )
        assert result == user.user_id

    @patch("app.services.payment_service.TeraidPayApiLog.warning")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_raises_when_user_not_found(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        embedding = [0.1, 0.2, 0.3]
        face_info = SimpleNamespace(user_id=123, distance=0.1)
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")

        mock_ssm_client_class.return_value = ssm_params
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = face_info
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundException):
            PaymentService().get_user_id_from_face_image(
                mysql_session=mysql_session,
                postgres_session=postgres_session,
                content=content,
            )

        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
        )
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=face_info.user_id,
        )
        mock_warning.assert_called_once()

    @patch("app.services.payment_service.TeraidPayApiLog.warning")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_raises_when_face_embedding_not_found(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        embedding = [0.1, 0.2, 0.3]
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")

        mock_ssm_client_class.return_value = ssm_params
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = None

        with pytest.raises(FaceEmbeddingNotFoundException):
            PaymentService().get_user_id_from_face_image(
                mysql_session=mysql_session,
                postgres_session=postgres_session,
                content=content,
            )

        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
        )
        mock_user_repository_class.assert_not_called()
        mock_warning.assert_called_once()

    @patch("app.services.payment_service.TeraidPayApiLog.warning")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_raises_when_nearest_face_exceeds_threshold(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        threshold = 0.42
        embedding = [0.1, 0.2, 0.3]
        face_info = SimpleNamespace(user_id=123, distance=0.4201)
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")

        mock_ssm_client_class.return_value = ssm_params
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = face_info

        with pytest.raises(FaceEmbeddingNotFoundException):
            PaymentService().get_user_id_from_face_image(
                mysql_session=mysql_session,
                postgres_session=postgres_session,
                content=content,
                threshold=threshold,
            )

        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
        )
        mock_user_repository_class.assert_not_called()
        mock_warning.assert_called_once()
