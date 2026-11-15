import pytest
from sqlalchemy.orm import Session

from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


class TestGetFaceEmbeddingById:
    """get_face_embedding_by_id の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_face_embedding_by_id_returns_face_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """指定した user_id の未削除 face_embedding を取得することを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=101,
        )

        assert result is not None
        assert result.user_id == 101
        assert result.embedding == [0.8] + [0.0] * 511
        assert result.is_active is True

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_face_embedding_by_id_returns_none_when_user_does_not_exist(
        self,
        postgres_session: Session,
    ) -> None:
        """指定した user_id の face_embedding が存在しない場合は None を返すことを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=999,
        )

        assert result is None
