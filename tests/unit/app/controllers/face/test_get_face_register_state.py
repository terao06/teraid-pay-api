from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.face_controller import faceController
from app.core.exceptions.custom_exception import (
    UserNotFoundException,
)
from app.core.exceptions.message import (
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR,
)
from app.models.responses.face_register_status_response import (
    FaceRegisterStatusResponse,
)


class TestGetFaceRegisterState:
    """get_face_register_state の動作を検証する。"""

    @patch("app.controllers.face_controller.FaceService")
    def test_get_face_register_state(self, mock_service_class) -> None:
        """正常系の処理結果を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        expected_response = FaceRegisterStatusResponse(
            user_id=user_id,
            is_registered=True,
        )
        mock_service = mock_service_class.return_value
        mock_service.get_face_register_state.return_value = expected_response

        result = faceController.get_face_register_state.__wrapped__.__wrapped__(
            faceController(),
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
        )

        mock_service.get_face_register_state.assert_called_once_with(
            postgres_session=postgres_session,
            mysql_session=mysql_session,
            user_id=user_id,
        )
        assert result == expected_response

    @patch("app.controllers.face_controller.FaceService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (UserNotFoundException("user not found"), 404, USER_NOT_FOUND_ERROR),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_get_face_register_state_raise_http_exception(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        mysql_session = Mock()
        user_id = 101
        mock_service = mock_service_class.return_value
        mock_service.get_face_register_state.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            faceController.get_face_register_state.__wrapped__.__wrapped__(
                faceController(),
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=user_id,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }
