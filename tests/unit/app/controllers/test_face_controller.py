from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.controllers.face_controller import faceController
from app.core.exceptions.custom_exception import (
    FaceConflictException,
    FaceNotFoundException,
    SameFaceFoundException,
)
from app.core.exceptions.message import (
    FACE_ALREADY_REGISTERED_ERROR,
    FACE_NOTE_FOUND_ERROR,
    REGISTER_FACE_ERROR,
    SAME_FACE_FOUND_ERROR,
    SERVER_ERROR,
)
from app.models.requests.face_register_request import (
    ExtensionType,
    FaceImageProcessingRequest,
)


class TestRegisterFace:
    @patch("app.controllers.face_controller.FaceService")
    def test_register_face(self, mock_service_class) -> None:
        postgres_session = Mock()
        request = FaceImageProcessingRequest(
            user_id=101,
            content="base64-encoded-image",
            extension_type=ExtensionType.PNG,
        )
        mock_service = mock_service_class.return_value
        mock_service.register_face.return_value = None

        result = faceController.register_face.__wrapped__(
            faceController(),
            postgres_session=postgres_session,
            request=request,
        )

        mock_service.register_face.assert_called_once_with(
            postgres_session=postgres_session,
            user_id=request.user_id,
            content=request.content,
            extension_type=request.extension_type,
        )
        assert result is None

    @patch("app.controllers.face_controller.FaceService")
    @pytest.mark.parametrize(
        ("side_effect", "expected_status_code", "expected_message"),
        [
            (FaceNotFoundException("face not found"), 400, FACE_NOTE_FOUND_ERROR),
            (SameFaceFoundException("same face found"), 400, SAME_FACE_FOUND_ERROR),
            (ValueError("invalid image"), 400, REGISTER_FACE_ERROR),
            (
                FaceConflictException("face already registered"),
                409,
                FACE_ALREADY_REGISTERED_ERROR,
            ),
            (Exception("unexpected error"), 500, SERVER_ERROR),
        ],
    )
    def test_register_face_raise_http_exception(
        self,
        mock_service_class,
        side_effect,
        expected_status_code,
        expected_message,
    ) -> None:
        postgres_session = Mock()
        request = FaceImageProcessingRequest(
            user_id=101,
            content="base64-encoded-image",
            extension_type=ExtensionType.PNG,
        )
        mock_service = mock_service_class.return_value
        mock_service.register_face.side_effect = side_effect

        with pytest.raises(HTTPException) as exc_info:
            faceController.register_face.__wrapped__(
                faceController(),
                postgres_session=postgres_session,
                request=request,
            )

        assert exc_info.value.status_code == expected_status_code
        assert exc_info.value.detail == {
            "status": "error",
            "message": expected_message,
        }
