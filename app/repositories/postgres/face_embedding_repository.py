from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding


class FaceEmbeddingRepository:
    def create_face_embedding(self, session: Session, face_embedding: FaceEmbedding) -> FaceEmbedding:
        """顔画像から取得したベクトルデータを登録する

        Args:
            session: SQLAlchemy のセッション。
            face_embedding: 保存する顔画像ベクトル情報。

        Returns:
            face_embedding: idを付与した顔画像ベクトル情報
        """
        session.add(face_embedding)
        session.flush()
        return face_embedding
