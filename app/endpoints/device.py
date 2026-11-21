"""端末の有効化、認証、来店セッション、注文、会計、メニュー参照を提供する。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Query, Response
from fastapi.security import HTTPAuthorizationCredentials

from app.controllers.device_controller import DeviceController
from app.controllers.device_payment_controller import DevicePaymentController
from app.dependencies.device_auth import device_bearer_scheme, get_device_token_uuid
from app.middlewares.request_wrapper import request_device_rapper
from app.middlewares.response_wrapper import response_device_rapper
from app.models.requests.device_access_token_request import DeviceAccessTokenRequest
from app.models.requests.device_activate_request import DeviceActivateRequest
from app.models.requests.device_checkout_create_request import DeviceCheckoutCreateRequest
from app.models.requests.device_face_payment_request import DeviceFacePaymentPathRequest, DeviceFacePaymentRequest
from app.models.requests.device_menu_category_list_request import DeviceMenuCategoryListRequest
from app.models.requests.device_menu_items_by_category_request import DeviceMenuItemsByCategoryRequest
from app.models.requests.device_order_create_request import DeviceOrderCreateRequest, DeviceOrderPathRequest
from app.models.requests.device_payment_result_request import DevicePaymentResultPathRequest
from app.models.requests.visit_session_start_request import VisitSessionStartRequest
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.models.responses.device_checkout_create_response import DeviceCheckoutCreateResponse
from app.models.responses.device_face_payment_response import DeviceFacePaymentResponse
from app.models.responses.device_menu_item_list_response import DeviceMenuItemListResponse
from app.models.responses.device_order_create_response import DeviceOrderCreateResponse
from app.models.responses.device_order_history_response import DeviceOrderHistoryResponse
from app.models.responses.device_payment_result_response import DevicePaymentResultResponse
from app.models.responses.menu_category_response import DeviceMenuCategoryListResponse
from app.models.responses.visit_session_start_response import VisitSessionStartResponse


device_router = APIRouter()


@device_router.post("/activate")
@response_device_rapper()
@request_device_rapper()
def activate_device(
    response: Response,
    request: DeviceActivateRequest,
) -> DeviceActivateResponse:
    """端末を初回有効化し、一度限りの端末認証情報を返す。

    Args:
        response: レスポンスデコレーターがキャッシュ制御を設定するレスポンス。
        request: 有効化コードを含むリクエスト。

    Returns:
        端末UUIDと端末認証情報。

    Raises:
        HTTPException: 有効化コードが無効、または有効化処理に失敗した場合。
    """
    return DeviceController().activate_device(request=request)


@device_router.post("/auth/token")
@response_device_rapper()
@request_device_rapper()
def issue_device_access_token(
    response: Response,
    request: DeviceAccessTokenRequest,
) -> DeviceAccessTokenResponse:
    """端末認証情報を照合し、アクセストークンを返す。

    Args:
        response: レスポンスデコレーターがキャッシュ制御を設定するレスポンス。
        request: 端末UUIDと認証情報を含むリクエスト。

    Returns:
        端末アクセストークン、トークン種別、有効期間。

    Raises:
        HTTPException: 端末認証に失敗した場合、または発行処理に失敗した場合。
    """
    return DeviceController().issue_device_access_token(request=request)


@device_router.post("/visit-sessions", status_code=201)
@response_device_rapper()
@request_device_rapper()
def start_visit_session(
    response: Response,
    request: VisitSessionStartRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> VisitSessionStartResponse:
    """認証済み端末の来店セッションを開始する。

    Args:
        response: HTTPステータスとキャッシュ制御を設定するレスポンス。
        request: 開始要求IDを含むリクエスト。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        新規または既存の来店セッションID。

    Raises:
        HTTPException: 端末認証の失敗、開始要求の競合、またはセッション開始の失敗。
    """
    device_uuid = get_device_token_uuid(credentials)
    result, created = DeviceController().start_visit_session(device_uuid=device_uuid, request=request)
    if not created:
        response.status_code = 200
    return result


@device_router.post("/visit-sessions/{visit_session_id}/orders", status_code=201)
@response_device_rapper()
@request_device_rapper()
def create_order(
    response: Response,
    path: Annotated[DeviceOrderPathRequest, Depends()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=64, pattern=r"\S")],
    request: DeviceOrderCreateRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceOrderCreateResponse:
    """認証済み端末から未払いの注文を受け付ける。

    Args:
        response: ステータスとキャッシュ制御を設定するレスポンス。
        path: 来店セッションIDを含む検証済みのパス入力。
        idempotency_key: 注文操作とその再送を識別するキー。
        request: 商品とオプションの明細。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        新規または登録済みの注文ID、合計金額、トークンシンボル。

    Raises:
        HTTPException: 端末認証、セッション確認、注文内容の検証、または登録に失敗した場合。
    """
    device_uuid = get_device_token_uuid(credentials)
    result, created = DeviceController().create_order(
        device_uuid=device_uuid,
        visit_session_id=path.visit_session_id,
        idempotency_key=idempotency_key,
        request=request,
    )
    if not created:
        response.status_code = 200
    return result


@device_router.get("/visit-sessions/{visit_session_id}/orders")
@response_device_rapper()
@request_device_rapper()
def get_order_history(
    response: Response,
    path: Annotated[DeviceOrderPathRequest, Depends()],
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceOrderHistoryResponse:
    """認証済み端末の来店セッションに属する注文履歴を返す。

    Args:
        response: 成功時のキャッシュ制御を設定するレスポンス。
        path: 来店セッションIDを含む検証済みのパス入力。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        来店セッション内の注文と保存済み明細。注文がない場合は空配列を含む。

    Raises:
        HTTPException: 端末認証失敗は401、対象セッションなしは404、取得失敗は500。
    """
    device_uuid = get_device_token_uuid(credentials)
    return DeviceController().get_order_history(device_uuid=device_uuid, visit_session_id=path.visit_session_id)


@device_router.post("/visit-sessions/{visit_session_id}/checkouts", status_code=201)
@response_device_rapper()
@request_device_rapper()
def create_checkout(
    response: Response,
    path: Annotated[DeviceOrderPathRequest, Depends()],
    request: Annotated[DeviceCheckoutCreateRequest, Body(discriminator="scope")],
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceCheckoutCreateResponse:
    """認証済み端末から未払い注文の会計作成を受け付ける。

    Args:
        response: 成功時のキャッシュ制御を設定するレスポンス。
        path: 来店セッションIDを含む検証済みのパス入力。
        request: 対象範囲と、個別会計の場合は対象注文ID。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        作成した会計ID、保存済みの注文・商品・オプションの明細、合計金額。

    Raises:
        HTTPException: 端末認証、セッションと注文の確認、または会計登録に失敗した場合。
    """
    device_uuid = get_device_token_uuid(credentials)
    return DeviceController().create_checkout(
        device_uuid=device_uuid,
        visit_session_id=path.visit_session_id,
        request=request,
    )


@device_router.post("/checkouts/{checkout_id}/payments/face", status_code=201)
@response_device_rapper()
@request_device_rapper()
def start_face_payment(
    response: Response,
    path: Annotated[DeviceFacePaymentPathRequest, Depends()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=64, pattern=r"\S")],
    request: DeviceFacePaymentRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceFacePaymentResponse:
    """認証済み端末の会計について顔照合で決済を開始する。

    Args:
        response: HTTPステータスとキャッシュ制御を設定するレスポンス。
        path: 会計IDを含む検証済みのパス入力。
        idempotency_key: 同じ支払い要求の再送を識別するキー。
        request: Base64形式の顔画像を含むリクエスト。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        既存または新規の決済試行IDと状態。

    Raises:
        HTTPException: 端末認証、会計の再照合、顔照合、または決済開始に失敗した場合。
    """
    device_uuid = get_device_token_uuid(credentials)
    result, response.status_code = DevicePaymentController().start_face_payment(
        device_uuid=device_uuid,
        checkout_id=path.checkout_id,
        idempotency_key=idempotency_key,
        request=request,
    )
    return result


@device_router.post("/checkouts/{checkout_id}/payments/{payment_request_id}/verify")
@response_device_rapper()
@request_device_rapper()
def verify_device_payment(
    response: Response,
    path: Annotated[DevicePaymentResultPathRequest, Depends()],
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DevicePaymentResultResponse:
    """認証済み端末に紐づく会計の決済結果を返す。

    Args:
        response: 成功時のキャッシュ制御を設定するレスポンス。
        path: 検証済みの会計IDと決済試行ID。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        決済試行ID、決済状態、来店セッション状態。

    Raises:
        HTTPException: 端末認証、対象の照会または決済結果の確定に失敗した場合。
    """
    device_uuid = get_device_token_uuid(credentials)
    return DevicePaymentController().verify_payment(
        device_uuid=device_uuid, checkout_id=path.checkout_id, payment_request_id=path.payment_request_id,
    )


@device_router.get("/menu/categories")
@response_device_rapper()
@request_device_rapper()
def get_menu_categories(
    response: Response,
    request: Annotated[DeviceMenuCategoryListRequest, Query()],
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceMenuCategoryListResponse:
    """注文受付中の来店セッション用に、端末の所属店舗のカテゴリーを返す。

    Args:
        response: キャッシュ制御を設定するレスポンス。
        request: 来店セッションIDを含む検証済みのクエリ。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        有効なカテゴリーの表示順の一覧。対象がない場合は空配列。

    Raises:
        HTTPException: 端末認証失敗は401、対象セッションなしは404、取得失敗は500。
    """
    device_uuid = get_device_token_uuid(credentials)
    return DeviceController().get_menu_categories(
        device_uuid=device_uuid,
        visit_session_id=request.visit_session_id,
    )


@device_router.get("/menu/categories/{menu_category_id}/items")
@response_device_rapper()
@request_device_rapper()
def get_menu_items_by_category(
    response: Response,
    request: Annotated[DeviceMenuItemsByCategoryRequest, Depends()],
    credentials: HTTPAuthorizationCredentials | None = Depends(device_bearer_scheme),
) -> DeviceMenuItemListResponse:
    """注文受付中の来店セッション向けに、指定カテゴリーのメニューを返す。

    Args:
        response: キャッシュ制御を設定するレスポンス。
        request: カテゴリーIDと来店セッションIDを含む検証済みのリクエスト。
        credentials: AuthorizationヘッダーのBearer認証情報。

    Returns:
        商品画像URLと選択可能なオプションを含むメニュー一覧。

    Raises:
        HTTPException: 端末認証、来店セッションの確認、またはメニューの取得に失敗した場合。
    """
    device_uuid = get_device_token_uuid(credentials)
    return DeviceController().get_menu_items_by_category(
        device_uuid=device_uuid,
        visit_session_id=request.visit_session_id,
        menu_category_id=request.menu_category_id,
    )
