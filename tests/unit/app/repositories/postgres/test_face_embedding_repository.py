import pytest
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding, ExtensionType
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


class TestCreateFaceEmbedding:
    """create_face_embedding の単体テスト。"""

    def test_create_face_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """user_id の登録がない場合は face_embedding を新規保存することを確認する。"""
        repository = FaceEmbeddingRepository()
        face_embedding = FaceEmbedding(
            user_id=101,
            embedding=[0.1] * 512,
            extension_type=ExtensionType.JPEG
        )

        result = repository.create_face_embedding(postgres_session, face_embedding)
        postgres_session.expire_all()

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.face_embedding_id == face_embedding.face_embedding_id)
            .one()
        )

        assert result is face_embedding
        assert saved_face_embedding.face_embedding_id is not None
        assert saved_face_embedding.user_id == 101
        assert saved_face_embedding.embedding == [0.1] * 512
        assert saved_face_embedding.is_active is True
        assert saved_face_embedding.extension_type == ExtensionType.JPEG
        assert saved_face_embedding.created_at is not None
        assert saved_face_embedding.updated_at is not None

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_create_face_embedding_creates_new_embedding_for_existing_user(
        self,
        postgres_session: Session,
    ) -> None:
        """同じ user_id の登録がある場合も face_embedding を新規保存することを確認する。"""
        repository = FaceEmbeddingRepository()
        existing_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 101)
            .one()
        )
        existing_face_embedding_id = existing_face_embedding.face_embedding_id
        existing_embedding = existing_face_embedding.embedding
        existing_extension_type = existing_face_embedding.extension_type

        new_face_embedding = FaceEmbedding(
            user_id=101,
            embedding=[0.2] * 512,
            extension_type=ExtensionType.JPEG,
            is_active=True,
        )
        result = repository.create_face_embedding(
            postgres_session,
            new_face_embedding,
        )
        postgres_session.expire_all()

        saved_face_embeddings = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 101)
            .order_by(FaceEmbedding.face_embedding_id)
            .all()
        )

        assert result is new_face_embedding
        assert result.face_embedding_id != existing_face_embedding_id
        assert len(saved_face_embeddings) == 2
        assert saved_face_embeddings[0].face_embedding_id == existing_face_embedding_id
        assert saved_face_embeddings[0].embedding == existing_embedding
        assert saved_face_embeddings[0].extension_type == existing_extension_type
        assert saved_face_embeddings[1].face_embedding_id == result.face_embedding_id
        assert saved_face_embeddings[1].embedding == [0.2] * 512
        assert saved_face_embeddings[1].is_active is True
        assert saved_face_embeddings[1].extension_type == ExtensionType.JPEG


class TestUpdateFaceEmbedding:
    """update_face_embedding の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_update_face_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """face_embedding を更新することを確認する。"""
        repository = FaceEmbeddingRepository()
        face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 102)
            .one()
        )
        face_embedding_id = face_embedding.face_embedding_id
        before_updated_at = face_embedding.updated_at

        face_embedding.extension_type = ExtensionType.PNG

        result = repository.update_face_embedding(postgres_session, face_embedding)
        postgres_session.flush()
        postgres_session.expire_all()

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.face_embedding_id == face_embedding_id)
            .one()
        )

        assert result is face_embedding
        assert saved_face_embedding.face_embedding_id == face_embedding_id
        assert saved_face_embedding.user_id == 102
        assert saved_face_embedding.embedding == [1.0] + [0.0] * 511
        assert saved_face_embedding.is_active is True
        assert saved_face_embedding.extension_type == ExtensionType.PNG
        assert saved_face_embedding.updated_at is not None
        assert saved_face_embedding.updated_at > before_updated_at


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


class TestDeleteFaceEmbedding:
    """delete_face_embedding の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_delete_face_embedding_deletes_row(
        self,
        postgres_session: Session,
    ) -> None:
        """face_embedding を物理削除することを確認する。"""
        repository = FaceEmbeddingRepository()
        face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 108)
            .one()
        )
        face_embedding_id = face_embedding.face_embedding_id

        result = repository.delete_face_embedding(postgres_session, face_embedding)
        postgres_session.flush()
        postgres_session.expire_all()

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.face_embedding_id == face_embedding_id)
            .one_or_none()
        )

        assert result is None
        assert saved_face_embedding is None


class TestGetNearestFaceEmbedding:
    """get_nearest_face_embedding の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_returns_first_matched_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """有効かつ未削除の候補から閾値内の最短ベクトルを取得することを確認する。"""
        repository = FaceEmbeddingRepository()
        query_embedding = [1.0] + [0.0] * 511

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=query_embedding,
            threshold=0.5,
            exclusion_user_id=101,
        )

        assert result is not None
        assert result.face_embedding.user_id == 102
        assert result.distance == pytest.approx(0.0)

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_returns_none_when_no_embedding_matches(
        self,
        postgres_session: Session,
    ) -> None:
        """閾値内の候補が存在しない場合は None を返すことを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=[-1.0] + [0.0] * 511,
            threshold=0.5,
            exclusion_user_id=101,
        )

        assert result is None

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
            threshold=0.5,
            exclusion_user_id=102,
        )

        assert result is not None
        assert result.face_embedding.user_id == 101
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
                threshold=0.7,
                exclusion_user_id=101,
            )
