import pytest
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding
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
        assert saved_face_embedding.created_at is not None
        assert saved_face_embedding.updated_at is not None
        assert saved_face_embedding.deleted_at is None

    def test_create_face_embedding_updates_existing_user_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """同じ user_id の登録がある場合は既存レコードを更新することを確認する。"""
        repository = FaceEmbeddingRepository()
        existing_face_embedding = FaceEmbedding(
            user_id=201,
            embedding=[0.1] * 512,
            is_active=True,
        )
        postgres_session.add(existing_face_embedding)
        postgres_session.flush()
        existing_face_embedding_id = existing_face_embedding.face_embedding_id

        result = repository.create_face_embedding(
            postgres_session,
            FaceEmbedding(
                user_id=201,
                embedding=[0.2] * 512,
                is_active=True,
            ),
        )
        postgres_session.expire_all()

        saved_face_embeddings = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 201)
            .all()
        )

        assert result.face_embedding_id == existing_face_embedding_id
        assert len(saved_face_embeddings) == 1
        assert saved_face_embeddings[0].face_embedding_id == existing_face_embedding_id
        assert saved_face_embeddings[0].embedding == [0.2] * 512
        assert saved_face_embeddings[0].is_active is True
        assert saved_face_embeddings[0].deleted_at is None


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
        assert result.deleted_at is None

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

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_face_embedding_by_id_returns_none_when_embedding_is_deleted(
        self,
        postgres_session: Session,
    ) -> None:
        """指定した user_id の face_embedding が削除済みの場合は None を返すことを確認する。"""
        repository = FaceEmbeddingRepository()

        result = repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=104,
        )

        assert result is None


class TestDeleteFaceEmbedding:
    """delete_face_embedding の単体テスト。"""

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_delete_face_embedding_sets_deleted_at_and_updated_at(
        self,
        postgres_session: Session,
    ) -> None:
        """face_embedding を物理削除せず、削除日時と更新日時を設定することを確認する。"""
        repository = FaceEmbeddingRepository()
        face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 108)
            .one()
        )
        face_embedding_id = face_embedding.face_embedding_id
        created_at = face_embedding.created_at
        embedding = face_embedding.embedding

        result = repository.delete_face_embedding(postgres_session, face_embedding)
        postgres_session.flush()
        postgres_session.expire_all()

        saved_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.face_embedding_id == face_embedding_id)
            .one()
        )

        assert result is face_embedding
        assert saved_face_embedding.face_embedding_id == face_embedding_id
        assert saved_face_embedding.user_id == 108
        assert saved_face_embedding.embedding == embedding
        assert saved_face_embedding.is_active is False
        assert saved_face_embedding.created_at == created_at
        assert saved_face_embedding.deleted_at is not None
        assert saved_face_embedding.updated_at == saved_face_embedding.deleted_at


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

    @pytest.mark.usefixtures("insert_face_embeddings")
    def test_get_nearest_face_embedding_excludes_deleted_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """deleted_at が設定された候補を検索対象外にすることを確認する。"""
        repository = FaceEmbeddingRepository()
        deleted_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == 106)
            .one()
        )

        result = repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=deleted_face_embedding.embedding,
            threshold=0.0,
            exclusion_user_id=101,
        )

        assert deleted_face_embedding.deleted_at is not None
        assert result is None

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
