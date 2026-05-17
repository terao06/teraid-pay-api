import base64
from io import BytesIO
from PIL import Image
from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.exceptions.custom_exception import FaceConflictException
from app.core.utils.logging import TeraidPayApiLog
from app.helpers.face_helper import FaceHelper
from app.models.postgres.face_embedding import FaceEmbedding
from app.models.requests.face_register_request import ExtensionType
from app.repositories.postgres.face_embedding_repository import FaceEmbeddingRepository


class FaceService:
    def register_face(
        self,
        postgres_session: Session,
        user_id: int,
        content: str, 
        extension_type: ExtensionType,
        threshold: float = 0.7) -> None:
        """認証用顔画像を登録する

        Args:
            session: SQLAlchemy のセッション。
            user_id: 顔画像に紐づけるユーザーID
            content: 顔画像
            extension_type: 顔画像の拡張子

        Returns:
            None
        """
        image_bytes = base64.b64decode(content)

        # NOTE: resizeすることでAIモデルの入力サイズに合わせる
        target_image = Image.open(BytesIO(image_bytes)).convert("RGB").resize((112, 112))
        ssm_params = SsmClient()
        s3_client = S3Client(s3_endpoint=ssm_params.s3_endpoint)
        face_embedding_repository = FaceEmbeddingRepository()

        scrfd_weight_bytes = s3_client.get_object(
            bucket_name=ssm_params.llm_weight_bucket,
            key=ssm_params.scrfd_weight
        )
        face_image = FaceHelper.get_face_landmark(weight_bytes=scrfd_weight_bytes, image=target_image)
        alignment_face = FaceHelper.alignment_face(face_image=face_image)

        adaface_weight_bytes = s3_client.get_object(
            bucket_name=ssm_params.llm_weight_bucket,
            key=ssm_params.adaface_weight
        )
        embedding = FaceHelper.get_embedding(weight_bytes=adaface_weight_bytes, face_image=alignment_face)

        face = face_embedding_repository.get_nearest_face_embedding(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
            exclusion_user_id=user_id,
        )
        if face is not None:
            TeraidPayApiLog.warning(f"この顔画像は既に登録されています。 user_id: {face.user_id}")
            raise FaceConflictException("この顔画像は既に登録されています。")

        embedding_info = FaceEmbedding(
            user_id=user_id,
            embedding=embedding,
            is_active=True,
        )

        face_embedding_repository.create_face_embedding(postgres_session=postgres_session, face_embedding=embedding_info)

        with BytesIO() as buffer:
            target_image.save(buffer, format=extension_type.value.upper())
            buffer.seek(0)

            s3_client.upload_object(
                bucket_name=ssm_params.face_image_bucket,
                file=buffer,
                filename=f"{user_id}.{extension_type.value}",
            )
