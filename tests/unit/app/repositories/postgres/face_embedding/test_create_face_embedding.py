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
