import pytest
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding, ExtensionType
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository

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
        assert saved_face_embedding.updated_at != before_updated_at
