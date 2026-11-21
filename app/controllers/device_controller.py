"""端末用APIのトランザクションとHTTPエラー変換を提供する。"""

import logging

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    CustomHttpException,
    DeviceActivationCodeInvalidException,
    DeviceCheckoutConflictException,
    DeviceCheckoutOrderNotFoundException,
    DeviceOrderConflictException,
    DeviceOrderInvalidException,
    MenuCategoryNotFoundException,
    UnauthorizedException,
    VisitSessionConflictException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import (
    DEVICE_ACTIVATION_CODE_INVALID_ERROR,
    DEVICE_AUTHENTICATION_FAILED_ERROR,
    DEVICE_CHECKOUT_ORDER_NOT_FOUND_ERROR,
    DEVICE_ORDER_CONFLICT_ERROR,
    DEVICE_ORDER_INVALID_ERROR,
    MENU_CATEGORY_NOT_FOUND_ERROR,
    SERVER_ERROR,
    VISIT_SESSION_CONFLICT_ERROR,
    VISIT_SESSION_NOT_FOUND_ERROR,
)
from app.middlewares.transaction import mysql_transaction
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.requests.device_checkout_create_request import DeviceCheckoutCreateRequest
from app.models.requests.device_order_create_request import DeviceOrderCreateRequest
from app.models.requests.visit_session_start_request import VisitSessionStartRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.models.responses.device_checkout_create_response import DeviceCheckoutCreateResponse
from app.models.responses.device_menu_item_list_response import DeviceMenuItemListResponse
from app.models.responses.device_order_create_response import DeviceOrderCreateResponse
from app.models.responses.device_order_history_response import DeviceOrderHistoryResponse
from app.models.responses.menu_category_response import DeviceMenuCategoryListResponse
from app.models.responses.visit_session_start_response import VisitSessionStartResponse
from app.services.device_order_service import DeviceOrderService
from app.services.device_service import DeviceService


logger = logging.getLogger(__name__)


class DeviceController:
    """端末用APIの業務処理を呼び出すコントローラー。

    Args:
        なし。

    Returns:
        端末用APIのコントローラー。
    """

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def activate_device(
        self,
        mysql_session: Session,
        request: DeviceActivateRequest,
    ) -> DeviceActivateResponse:
        """初回有効化をコミットし、失敗時はHTTP例外に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            request: 検証済みの有効化リクエスト。

        Returns:
            コミット済みの端末UUIDと端末認証情報。

        Raises:
            HTTPException: コードを利用できない場合は400、処理に失敗した場合は500。
        """
        try:
            return DeviceService().activate_device(
                mysql_session=mysql_session,
                activation_code=request.activation_code,
            )
        except DeviceActivationCodeInvalidException:
            raise CustomHttpException.get_http_exception(
                status_code=400,
                message=DEVICE_ACTIVATION_CODE_INVALID_ERROR,
            ) from None
        except Exception as error:
            logger.error("端末初回有効化処理に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            ) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def issue_device_access_token(
        self,
        mysql_session: Session,
        request: DeviceAccessTokenRequest,
    ) -> DeviceAccessTokenResponse:
        """最終認証日時の更新をコミットした後にアクセストークンを返す。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            request: 検証済みの端末認証リクエスト。

        Returns:
            端末アクセストークン、トークン種別、有効期間。

        Raises:
            HTTPException: 端末認証に失敗した場合は401、発行処理に失敗した場合は500。
        """
        try:
            return DeviceService().issue_device_access_token(
                mysql_session=mysql_session,
                device_uuid=str(request.device_uuid),
                device_credential=request.device_credential,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
            ) from None
        except Exception as error:
            logger.error("端末アクセストークン発行処理に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            ) from None


    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def start_visit_session(
        self,
        mysql_session: Session,
        device_uuid: str,
        request: VisitSessionStartRequest,
    ) -> tuple[VisitSessionStartResponse, bool]:
        """端末の利用状態を確認し、来店セッション開始の結果をコミットする。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            request: 検証済みの来店セッション開始リクエスト。

        Returns:
            来店セッションのレスポンスと、新規作成した場合にTrueとなるフラグ。

        Raises:
            HTTPException: 端末が利用できない場合は401、競合は409、処理失敗は500。
        """
        try:
            visit_session_id, created = DeviceService().start_visit_session(
                mysql_session=mysql_session,
                device_uuid=device_uuid,
                start_request_id=request.start_request_id,
            )
            return VisitSessionStartResponse(visit_session_id=visit_session_id), created
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=409,
                message=VISIT_SESSION_CONFLICT_ERROR,
            ) from None
        except Exception as error:
            logger.error("来店セッション開始処理に失敗しました (%s)", type(error).__name__)
            raise CustomHttpException.get_http_exception(
                status_code=500,
                message=SERVER_ERROR,
            ) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def create_order(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        idempotency_key: str,
        request: DeviceOrderCreateRequest,
    ) -> tuple[DeviceOrderCreateResponse, bool]:
        """注文登録をコミットし、業務例外をHTTP応答に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末のUUID。
            visit_session_id: 来店セッションID。
            idempotency_key: 注文操作とその再送を識別するキー。
            request: 検証済みの注文内容。

        Returns:
            保存された注文のレスポンスと、新規登録の場合にTrueとなるフラグ。

        Raises:
            HTTPException: 端末認証失敗は401、対象セッションなしは404、競合は409、
                注文内容の不備は422、DB処理やコミットの失敗は500。
        """
        try:
            return DeviceOrderService().create_order(
                mysql_session=mysql_session,
                device_uuid=device_uuid,
                visit_session_id=visit_session_id,
                idempotency_key=idempotency_key,
                request=request,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=VISIT_SESSION_NOT_FOUND_ERROR,
            ) from None
        except DeviceOrderConflictException:
            raise CustomHttpException.get_http_exception(
                status_code=409,
                message=DEVICE_ORDER_CONFLICT_ERROR,
            ) from None
        except DeviceOrderInvalidException:
            raise CustomHttpException.get_http_exception(
                status_code=422,
                message=DEVICE_ORDER_INVALID_ERROR,
            ) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def create_checkout(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        request: DeviceCheckoutCreateRequest,
    ) -> DeviceCheckoutCreateResponse:
        """会計と対象注文をコミットし、業務例外をHTTP応答に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末のUUID。
            visit_session_id: 会計を作成する来店セッションID。
            request: 検証済みの対象範囲と注文ID。

        Returns:
            コミット済みの会計ID、対象注文の明細、合計金額、トークンシンボル。

        Raises:
            HTTPException: 端末認証失敗は401、対象セッション・注文なしは404、
                決済状態や通貨の競合は409、DB処理やコミットの失敗は500。
        """
        try:
            return DeviceOrderService().create_checkout(
                mysql_session=mysql_session,
                device_uuid=device_uuid,
                visit_session_id=visit_session_id,
                request=request,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404, message=VISIT_SESSION_NOT_FOUND_ERROR
            ) from None
        except DeviceCheckoutOrderNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404, message=DEVICE_CHECKOUT_ORDER_NOT_FOUND_ERROR
            ) from None
        except DeviceCheckoutConflictException as error:
            raise CustomHttpException.get_http_exception(status_code=409, message=str(error)) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def get_order_history(
        self, mysql_session: Session, device_uuid: str, visit_session_id: int
    ) -> DeviceOrderHistoryResponse:
        """注文履歴を取得し、端末と来店セッションの例外をHTTP応答に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末アクセストークンのUUID。
            visit_session_id: 取得対象の来店セッションID。

        Returns:
            来店セッション内の注文と商品・オプション明細。

        Raises:
            HTTPException: 端末認証失敗は401、対象セッションなしは404、取得失敗は500。
        """
        try:
            return DeviceOrderService().get_order_history(mysql_session, device_uuid, visit_session_id)
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=VISIT_SESSION_NOT_FOUND_ERROR,
            ) from None


    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def get_menu_categories(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
    ) -> DeviceMenuCategoryListResponse:
        """カテゴリー一覧を取得し、端末や来店セッションの例外をHTTP応答に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 端末が指定した来店セッションID。

        Returns:
            端末の所属店舗の有効なカテゴリー一覧。

        Raises:
            HTTPException: 端末が利用できない場合は401、対象セッションなしは404、取得失敗は500。
        """
        try:
            return DeviceService().get_menu_categories(
                mysql_session=mysql_session,
                device_uuid=device_uuid,
                visit_session_id=visit_session_id,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=VISIT_SESSION_NOT_FOUND_ERROR,
            ) from None

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def get_menu_items_by_category(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        menu_category_id: int,
    ) -> DeviceMenuItemListResponse:
        """カテゴリー別メニューを取得し、業務例外をHTTP応答に変換する。

        Args:
            mysql_session: デコレーターが渡すMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 端末が指定した来店セッションID。
            menu_category_id: 端末が指定したメニューカテゴリーID。

        Returns:
            販売可能な商品と選択可能なオプションの一覧。

        Raises:
            HTTPException: 端末が利用できない場合は401、セッションやカテゴリーが対象外の場合は404、処理失敗は500。
        """
        try:
            return DeviceService().get_menu_items_by_category(
                mysql_session=mysql_session,
                device_uuid=device_uuid,
                visit_session_id=visit_session_id,
                menu_category_id=menu_category_id,
            )
        except UnauthorizedException:
            raise CustomHttpException.get_http_exception(
                status_code=401,
                message=DEVICE_AUTHENTICATION_FAILED_ERROR,
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        except VisitSessionNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=VISIT_SESSION_NOT_FOUND_ERROR,
            ) from None
        except MenuCategoryNotFoundException:
            raise CustomHttpException.get_http_exception(
                status_code=404,
                message=MENU_CATEGORY_NOT_FOUND_ERROR,
            ) from None
