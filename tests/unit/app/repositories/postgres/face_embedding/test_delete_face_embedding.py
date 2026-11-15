import pytest
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


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
