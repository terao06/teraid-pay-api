from sqlalchemy import Float, bindparam, cast
from sqlalchemy.orm import Session

from app.models.postgres.face_embedding import FaceEmbedding


class FaceEmbeddingRepository:
    def create_face_embedding(self, postgres_session: Session, face_embedding: FaceEmbedding) -> FaceEmbedding:
        """顔画像から取得したベクトルデータを登録または更新する。

        Args:
            postgres_session: SQLAlchemy のセッション。
            face_embedding: 保存する顔画像ベクトル情報。

        Returns:
            face_embedding: 登録または更新した顔画像ベクトル情報。
        """
        existing_face_embedding = (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.user_id == face_embedding.user_id)
            .first()
        )
        if existing_face_embedding is not None:
            existing_face_embedding.embedding = face_embedding.embedding
            existing_face_embedding.is_active = face_embedding.is_active
            existing_face_embedding.deleted_at = face_embedding.deleted_at
            postgres_session.flush()
            return existing_face_embedding

        postgres_session.add(face_embedding)
        postgres_session.flush()
        return face_embedding

    def get_nearest_face_embedding(
        self,
        postgres_session: Session,
        embedding: list[float],
        threshold: float,
        exclusion_user_id: int,
    ) -> FaceEmbedding | None:
        """指定したベクトルに最も近い有効な顔特徴量を取得する。

        Args:
            postgres_session: SQLAlchemy のセッション。
            embedding: 検索対象の顔特徴量ベクトル。
            threshold: 取得対象とする距離の閾値。
            exclusion_user_id: 検索対象から除外するユーザーID。

        Returns:
            face_embedding: 最も近い顔特徴量。該当がない場合は None。
        """
        embedding_values = self._validate_embedding(embedding)
        distance = FaceEmbedding.embedding.op("<->", return_type=Float)(
            cast(
                bindparam(
                    "embedding",
                    embedding_values,
                    type_=FaceEmbedding.embedding.type,
                ),
                FaceEmbedding.embedding.type,
            )
        )

        return (
            postgres_session.query(FaceEmbedding)
            .filter(FaceEmbedding.is_active.is_(True))
            .filter(FaceEmbedding.deleted_at.is_(None))
            .filter(FaceEmbedding.user_id != exclusion_user_id)
            .filter(distance <= threshold)
            .order_by(distance)
            .first()
        )

    def _validate_embedding(self, embedding: list[float]) -> list[float]:
        dimensions = FaceEmbedding.embedding.type.dimensions
        if len(embedding) != dimensions:
            raise ValueError(f"embedding は {dimensions} 次元である必要があります。")
        return embedding
