from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


class TestCreateFaceEmbedding:
    """create_face_embedding の単体テスト。"""

    def test_create_face_embedding(
        self,
        postgres_session: Session,
    ) -> None:
        """face_embedding を保存し、flush 済みの内容を取得できることを確認する。"""
        repository = FaceEmbeddingRepository()
        face_embedding = FaceEmbedding(
            face_embedding_id=1,
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
        assert saved_face_embedding.face_embedding_id == 1
        assert saved_face_embedding.user_id == 101
        assert saved_face_embedding.embedding == [0.1] * 512
        assert saved_face_embedding.is_active is True
        assert saved_face_embedding.created_at is not None
        assert saved_face_embedding.updated_at is not None
        assert saved_face_embedding.deleted_at is None
