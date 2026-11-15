from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    FaceEmbeddingAlreadyRegisterException,
    UserNotFoundException,
)


from ._helpers import build_face_service


class TestFaceValidation:
    """face_validation の動作を検証する。"""

    @patch("app.services.face_service.UserRepository")
    def test_validate_user_exists_returns_none_when_user_exists(
        self,
        mock_user_repository_class,
    ) -> None:
        """対象が存在しない場合の戻り値を検証する。"""
        mysql_session = Mock()
        user_id = 101
        user = Mock()
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user

        service = build_face_service(user_repository=mock_user_repository)

        result = service._validate_user_exists(
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result is None
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    @patch("app.services.face_service.UserRepository")
    def test_validate_user_exists_raises_user_not_found_when_user_does_not_exist(
        self,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        user_id = 999
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundException, match="ユーザーが存在しません。"):
            service = build_face_service(user_repository=mock_user_repository)
            service._validate_user_exists(
                mysql_session=mysql_session,
                user_id=user_id,
            )

        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "対象のユーザーは存在しません。 user_id: 999"
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    def test_validate_face_not_registered_raises_already_registered_when_face_exists(
        self,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        user_id = 101
        registered_face = Mock()
        service = build_face_service()
        service.face_embedding_repository.get_face_embedding_by_id.return_value = registered_face

        with pytest.raises(FaceEmbeddingAlreadyRegisterException, match="すでに顔画像が登録されています。"):
            service._validate_face_not_registered(
                postgres_session=postgres_session,
                user_id=user_id,
            )

        service.face_embedding_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "すでに顔画像が登録されています。 user_id: 101"
        )
