import base64
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import (
    FaceConflictException,
    FaceEmbeddingAlreadyRegisterException,
    FaceEmbeddingNotFoundException,
    UserNotFoundException,
)
from app.core.utils.logging import TeraidPayApiLog
from app.helpers.face_helper import FaceHelper
from app.models.mysql.user import User
from app.models.postgres.face_embedding import FaceEmbedding, ExtensionType
from app.models.responses.face_register_status_response import FaceRegisterStatusResponse
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository
from app.repositories.mysql.user_repository import UserRepository


class FaceService:
    """顔登録関連処理を担当するサービス。"""

    def __init__(self) -> None:
        self.face_embedding_repository = FaceEmbeddingRepository()
        self.user_repository = UserRepository()
        self.ssm_params = SsmClient()
        self.s3_client = S3Client(s3_endpoint=self.ssm_params.s3_endpoint)

    def get_face_register_state(
        self,
        postgres_session: Session,
        mysql_session: Session,
        user_id: int) -> FaceRegisterStatusResponse:
        """認証用顔画像を登録する

        Args:
            postgres_session: SQLAlchemy のセッション。
            mysql_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID

        Returns:
            FaceRegisterStatusResponse: 顔登録状況結果レスポンス
        """
        self._validate_user_exists(mysql_session=mysql_session, user_id=user_id)
        user_face_embedding = self.face_embedding_repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=user_id
        )
        return FaceRegisterStatusResponse(
            user_id=user_id,
            is_registered=user_face_embedding is not None
        )

    def register_face(
        self,
        postgres_session: Session,
        mysql_session: Session,
        user_id: int,
        content: str, 
        extension_type: ExtensionType,
        threshold: float = 0.7) -> None:
        """認証用顔画像を登録する

        Args:
            postgres_session: SQLAlchemy のセッション。
            mysql_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID
            content: 顔画像
            extension_type: 顔画像の拡張子
            threshold: 閾値

        Returns:
            None
        """
        self._validate_user_exists(mysql_session=mysql_session, user_id=user_id)
        self._validate_face_not_registered(
            postgres_session=postgres_session,
            user_id=user_id
        )
        image_bytes = base64.b64decode(content)
        target_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        embedding = self._get_embedding_from_image(image=target_image)

        self._validate_face_embedding(
            postgres_session=postgres_session,
            threshold=threshold,
            user_id=user_id,
            embedding=embedding
        )

        embedding_info = FaceEmbedding(
            user_id=user_id,
            embedding=embedding,
            extension_type=extension_type,
            is_active=True,
        )

        self.face_embedding_repository.create_face_embedding(postgres_session=postgres_session, face_embedding=embedding_info)

        with BytesIO() as buffer:
            target_image.save(buffer, format=extension_type.value.upper())
            buffer.seek(0)

            self.s3_client.upload_object(
                bucket_name=self.ssm_params.face_image_bucket,
                file=buffer,
                file_name=f"{user_id}.{extension_type.value}",
            )

    def update_face(
        self,
        postgres_session: Session,
        mysql_session: Session,
        user_id: int,
        content: str, 
        extension_type: ExtensionType,
        threshold: float = 0.7) -> None:
        """認証用顔画像を登録する

        Args:
            postgres_session: SQLAlchemy のセッション。
            mysql_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID
            content: 顔画像
            extension_type: 顔画像の拡張子
            threshold: 閾値

        Returns:
            None
        """
        self._validate_user_exists(mysql_session=mysql_session, user_id=user_id)
        register_embedding = self._get_registered_face_embedding(
            postgres_session=postgres_session,
            user_id=user_id
        )
        image_bytes = base64.b64decode(content)
        target_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        embedding = self._get_embedding_from_image(image=target_image)

        self._validate_face_embedding(
            postgres_session=postgres_session,
            threshold=threshold,
            user_id=user_id,
            embedding=embedding
        )

        register_embedding.embedding = embedding
        register_embedding.extension_type = extension_type
        self.face_embedding_repository.update_face_embedding(
            postgres_session=postgres_session,
            face_embedding=register_embedding
        )

        with BytesIO() as buffer:
            target_image.save(buffer, format=extension_type.value.upper())
            buffer.seek(0)

            self.s3_client.upload_object(
                bucket_name=self.ssm_params.face_image_bucket,
                file=buffer,
                file_name=f"{user_id}.{extension_type.value}",
            )

    def delete_face(self, postgres_session: Session, mysql_session: Session, user_id: int) -> None:
        """認証用顔画像を削除する

        Args:
            postgres_session: SQLAlchemy のセッション。
            mysql_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID

        Returns:
            None
        """
        self._validate_user_exists(mysql_session=mysql_session, user_id=user_id)
        target_embedding = self._get_registered_face_embedding(
            postgres_session=postgres_session,
            user_id=user_id
        )

        self.face_embedding_repository.delete_face_embedding(
            postgres_session=postgres_session,
            face_embedding=target_embedding
        )

        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        s3_client.delete_object(
                bucket_name=ssm_params.face_image_bucket,
                file_name=f"{user_id}.{target_embedding.extension_type.value}",
            )

    def _validate_user_exists(self, mysql_session: Session, user_id: int) -> None:
        """ユーザーが存在するかのバリデーションを行う

        Args:
            mysql_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID

        Returns:
            None
        """
        user = self.user_repository.get_user_by_id(
            mysql_session=mysql_session,
            user_id=user_id
        )

        if user is None:
            TeraidPayApiLog.warning(f"対象のユーザーは存在しません。 user_id: {user_id}")
            raise UserNotFoundException("ユーザーが存在しません。")

    def _validate_face_not_registered(
        self,
        postgres_session: Session,
        user_id: int
    ) -> None:
        """顔画像が登録されていないか確認するバリデーションを行う

        Args:
            postgres_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID

        Returns:
            None
        """
        face_embedding = self.face_embedding_repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=user_id
        )

        if face_embedding is not None:
            TeraidPayApiLog.warning(f"すでに顔画像が登録されています。 user_id: {user_id}")
            raise FaceEmbeddingAlreadyRegisterException(
                "すでに顔画像が登録されています。"
            )

    def _get_registered_face_embedding(
        self,
        postgres_session: Session,
        user_id: int
    ) -> FaceEmbedding:
        """顔画像が登録されているか確認するバリデーションを行う

        Args:
            postgres_session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID

        Returns:
            FaceEmbedding: 顔画像情報
        """
        face_embedding = self.face_embedding_repository.get_face_embedding_by_id(
            postgres_session=postgres_session,
            user_id=user_id
        )

        if face_embedding is None:
            TeraidPayApiLog.warning(f"対象のユーザーIDに顔画像は登録されていません。 user_id: {user_id}")
            raise FaceEmbeddingNotFoundException(
                "顔画像が登録されていません。"
            )

        return face_embedding

    def _validate_face_embedding(
            self,
            postgres_session: Session,
            threshold: float,
            user_id: int,
            embedding: list[float]) -> None:
        """同一顔画像が別ユーザーに登録されていないかバリデーションを行う

        Args:
            postgres_session: SQLAlchemy のセッション。
            threshold: 閾値
            user_id: 顔画像に紐づけるユーザーID
            embedding: 顔のランドマーク

        Returns:
            None
        """
        face = self.face_embedding_repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
            exclusion_user_id=user_id,
        )
        if face is not None:
            TeraidPayApiLog.warning(
                f"この顔画像は既に登録されています。 "
                f"user_id: {face.face_embedding.user_id}, distance: {face.distance}"
            )
            raise FaceConflictException("この顔画像は既に登録されています。")

    def _get_embedding_from_image(self, image: Image) -> list[float]:
        """画像から顔のlandmarkを抽出する

        Args:
            image: 顔画像

        Returns:
            FaceEmbedding: 顔画像から抽出したランドマーク
        """

        scrfd_weight_bytes = self.s3_client.get_object(
            bucket_name=self.ssm_params.llm_weight_bucket,
            key=self.ssm_params.scrfd_weight
        )
        face_image = FaceHelper.get_face_landmark(weight_bytes=scrfd_weight_bytes, image=image)
        alignment_face = FaceHelper.alignment_face(face_image=face_image)

        adaface_weight_bytes = self.s3_client.get_object(
            bucket_name=self.ssm_params.llm_weight_bucket,
            key=self.ssm_params.adaface_weight
        )
        return FaceHelper.get_embedding(weight_bytes=adaface_weight_bytes, face_image=alignment_face)
