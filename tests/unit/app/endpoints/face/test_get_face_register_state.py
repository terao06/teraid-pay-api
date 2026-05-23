from unittest.mock import patch

from fastapi import HTTPException
import pytest

from app.models.responses.face_register_status_response import FaceRegisterStatusResponse


class TestGetFaceRegisterState:
    """get_face_register_state endpoint unit tests."""

    @patch("app.endpoints.face.faceController.get_face_register_state")
    def test_get_face_register_state_returns_wrapped_success(
        self,
        mock_get_face_register_state,
        client,
    ) -> None:
        mock_get_face_register_state.return_value = FaceRegisterStatusResponse(
            user_id=101,
            is_registered=True,
        )

        response = client.get("/face/101")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "user_id": 101,
                "is_registered": True,
            },
        }
        mock_get_face_register_state.assert_called_once()
        assert mock_get_face_register_state.call_args.kwargs["user_id"] == 101

    @patch("app.endpoints.face.faceController.get_face_register_state")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (404, "user not found"),
            (500, "server error"),
        ],
    )
    def test_get_face_register_state_returns_http_exception_from_controller(
        self,
        mock_get_face_register_state,
        status_code,
        message,
        client,
    ) -> None:
        mock_get_face_register_state.side_effect = HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
            },
        )

        response = client.get("/face/101")

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
    @pytest.mark.parametrize(
        ("user_id", "is_registered"),
        [
            (101, True),
            (110, False),
        ],
    )
    def test_with_db_returns_face_register_state(
        self,
        user_id,
        is_registered,
        client_with_db,
    ) -> None:
        response = client_with_db.get(f"/face/{user_id}")

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "user_id": user_id,
                "is_registered": is_registered,
            },
        }
