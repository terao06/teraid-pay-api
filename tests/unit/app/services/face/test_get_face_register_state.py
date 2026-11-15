from unittest.mock import Mock

import pytest

from app.core.exceptions.custom_exception import (
    UserNotFoundException,
)


from ._helpers import build_face_service


class TestGetFaceRegisterState:
    """get_face_register_state の動作を検証する。"""

    def test_get_face_register_state_returns_registered_when_face_exists(self) -> None:
        """正常系の処理結果を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        registered_face = Mock()
        service = build_face_service()
        service._validate_user_exists = Mock()
        service.face_embedding_repository.get_face_embedding_by_id.return_value = registered_face

        result = service.get_face_register_state(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result.user_id == user_id
        assert result.is_registered is True
        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service.face_embedding_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )

    def test_get_face_register_state_returns_not_registered_when_face_does_not_exist(self) -> None:
        """対象が存在しない場合の戻り値を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        service = build_face_service()
        service._validate_user_exists = Mock()
        service.face_embedding_repository.get_face_embedding_by_id.return_value = None

        result = service.get_face_register_state(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
        )

        assert result.user_id == user_id
        assert result.is_registered is False
        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service.face_embedding_repository.get_face_embedding_by_id.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=user_id,
        )

    def test_get_face_register_state_raises_user_not_found_when_user_does_not_exist(self) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 999
        service = build_face_service()
        service._validate_user_exists = Mock(
            side_effect=UserNotFoundException("user not found")
        )

        with pytest.raises(UserNotFoundException, match="user not found"):
            service.get_face_register_state(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
            )

        service._validate_user_exists.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        service.face_embedding_repository.get_face_embedding_by_id.assert_not_called()
