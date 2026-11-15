from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    FaceConflictException,
)


from ._helpers import build_face_service


class TestValidateFaceEmbedding:
    """validate_face_embedding の動作を検証する。"""

    def test_validate_face_embedding_returns_none_when_same_face_does_not_exist(self) -> None:
        """対象が存在しない場合の戻り値を検証する。"""
        postgres_session = Mock()
        user_id = 101
        threshold = 0.7
        embedding = [0.1] * 512
        service = build_face_service()
        service.face_embedding_repository.get_nearest_face_embedding.return_value = None

        result = service._validate_face_embedding(
            postgres_session=postgres_session,
            threshold=threshold,
            user_id=user_id,
            embedding=embedding,
        )

        assert result is None
        service.face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            exclusion_user_id=user_id,
        )

    @patch("app.services.face_service.TeraidPayApiLog.warning")
    def test_validate_face_embedding_raises_conflict_when_same_face_exists(
        self,
        mock_warning,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        postgres_session = Mock()
        user_id = 101
        threshold = 0.7
        embedding = [0.1] * 512
        nearest_face = SimpleNamespace(
            user_id=202,
            distance=0.1234,
        )
        service = build_face_service()
        service.face_embedding_repository.get_nearest_face_embedding.return_value = nearest_face

        with pytest.raises(FaceConflictException, match="この顔画像は既に登録されています。"):
            service._validate_face_embedding(
                postgres_session=postgres_session,
                threshold=threshold,
                user_id=user_id,
                embedding=embedding,
            )

        service.face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            exclusion_user_id=user_id,
        )
        mock_warning.assert_called_once_with(
            "この顔画像は既に登録されています。 user_id: 202, distance: 0.1234"
        )

    def test_validate_face_embedding_returns_none_when_nearest_face_exceeds_threshold(self) -> None:
        """対象が存在しない場合の戻り値を検証する。"""
        postgres_session = Mock()
        user_id = 101
        threshold = 0.7
        embedding = [0.1] * 512
        nearest_face = SimpleNamespace(
            user_id=202,
            distance=0.7001,
        )
        service = build_face_service()
        service.face_embedding_repository.get_nearest_face_embedding.return_value = nearest_face

        result = service._validate_face_embedding(
            postgres_session=postgres_session,
            threshold=threshold,
            user_id=user_id,
            embedding=embedding,
        )

        assert result is None
        service.face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            exclusion_user_id=user_id,
        )
