from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    FaceConflictException,
    FaceEmbeddingNotFoundException,
    FaceNotFoundException,
    SameFaceFoundException,
    UserNotFoundException
)
from app.core.exceptions.message import (
    FACE_ALREADY_REGISTERED_ERROR,
    FACE_NOT_REGISTERED_ERROR,
    FACE_NOTE_FOUND_ERROR,
    REGISTER_FACE_ERROR,
    SAME_FACE_FOUND_ERROR,
    SERVER_ERROR,
    USER_NOT_FOUND_ERROR
)
from app.middlewares.transaction import postgres_transaction, mysql_transaction
from app.models.requests.face_delete_request import FaceDeleteRequest
from app.models.requests.face_register_request import FaceRegisterRequest
from app.services.face_service import FaceService


class faceController:
    """顔認証 API のリクエストを処理するコントローラーです。"""

    @postgres_transaction
    @mysql_transaction
    def register_face(self, postgres_session: Session, mysql_session: Session, request: FaceRegisterRequest) -> None:
        """顔画像を登録する

        Args:
            postgres_session: SQLAlchemy のセッションです。
            request: 顔画像登録リクエストパラメータ

        Returns:
            None
        """
        try:
            return FaceService().register_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=request.user_id,
                content=request.content,
                extension_type=request.extension_type)

        except UserNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=USER_NOT_FOUND_ERROR)

        except FaceNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=FACE_NOTE_FOUND_ERROR)

        except SameFaceFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=SAME_FACE_FOUND_ERROR)

        except ValueError:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=REGISTER_FACE_ERROR)
        
        except FaceConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=409,
                message=FACE_ALREADY_REGISTERED_ERROR)
        
        except Exception:
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)

    @postgres_transaction
    @mysql_transaction
    def delete_face(self, postgres_session: Session, mysql_session: Session, request: FaceDeleteRequest) -> None:
        """顔画像を削除する

        Args:
            postgres_session: SQLAlchemy のセッションです。
            request: 顔画像削除リクエストパラメータ

        Returns:
            None
        """
        try:
            return FaceService().delete_face(
                postgres_session=postgres_session,
                mysql_session=mysql_session,
                user_id=request.user_id)

        except UserNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=USER_NOT_FOUND_ERROR)

        except FaceEmbeddingNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=FACE_NOT_REGISTERED_ERROR)

        except Exception as e:
            print("####################")
            print(e)
            print("####################")
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR)
