import pytest
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import ExtensionType
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


class TestGetNearestFaceEmbedding:
    """get_nearest_face_embedding の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_returns_first_matched_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """有効な候補から最短ベクトルを取得することを確認する。"""
        repository = FaceEmbeddingRepository()
        query_embedding = [1.0] + [0.0] * 511

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=query_embedding,
            exclusion_user_id=101,
        )

        assert result is not None
        assert result.user_id == 102
        assert result.distance == pytest.approx(0.0)

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_returns_nearest_even_when_outside_threshold(
        self,
        postgres_session: Session,
    ) -> None:
        """閾値比較をせず、最も近い候補を返すことを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=[-1.0] + [0.0] * 511,
            exclusion_user_id=101,
        )

        assert result is not None
        assert result.user_id == 108
        assert result.distance == pytest.approx(1.118033988749895)

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_does_not_exclude_when_exclusion_user_id_is_none(
        self,
        postgres_session: Session,
    ) -> None:
        """除外対象のユーザーIDが未指定の場合は全ユーザーを検索対象にすることを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=[1.0] + [0.0] * 511,
            exclusion_user_id=None,
        )

        assert result is not None
        assert result.user_id == 102
        assert result.embedding == [1.0] + [0.0] * 511
        assert result.is_active is True
        assert result.extension_type == ExtensionType.JPEG
        assert result.created_at is not None
        assert result.updated_at is not None
        assert result.distance == pytest.approx(0.0)

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_excludes_specified_user_id(
        self,
        postgres_session: Session,
    ) -> None:
        """除外対象のユーザーIDに紐づく候補を検索対象外にすることを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=[1.0] + [0.0] * 511,
            exclusion_user_id=102,
        )

        assert result is not None
        assert result.user_id == 101
        assert result.distance == pytest.approx(0.2)

    def test_get_nearest_face_embedding_rejects_invalid_embedding_dimensions(
        self,
        postgres_session: Session,
    ) -> None:
        """512 次元以外の embedding を受け取った場合は ValueError を送出する。"""
        repository = FaceEmbeddingRepository()

        with pytest.raises(ValueError, match="embedding は 512 次元である必要があります。"):
            repository.get_nearest_face_embedding(
                postgres_session=postgres_session,
                embedding=[0.1] * 511,
                exclusion_user_id=101,
            )
