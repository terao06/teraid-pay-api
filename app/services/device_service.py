"""端末の有効化、認証、来店セッションの開始・終了、メニュー参照の業務処理を提供する。"""

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.core.config.device_auth import get_device_auth_config
from app.core.exceptions.custom_exception import (
    DeviceActivationCodeInvalidException,
    MenuCategoryNotFoundException,
    UnauthorizedException,
    VisitSessionCompletionConflictException,
    VisitSessionConflictException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import DEVICE_CHECKOUT_PROCESSING_ERROR, VISIT_SESSION_UNPAID_ORDERS_ERROR
from app.core.utils.datetime import JST
from app.core.utils.device_activation import hash_device_secret
from app.core.utils.device_auth import DeviceAuthUtil
from app.helpers.menu_category_image_helper import MenuCategoryImageHelper
from app.models.mysql.device import Device
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.models.responses.device_menu_item_list_response import (
    DeviceMenuItemListResponse,
    DeviceMenuItemResponse,
    DeviceMenuOptionGroupResponse,
    DeviceMenuOptionResponse,
)
from app.models.responses.menu_category_response import (
    DeviceMenuCategoryListResponse,
    MenuCategoryDisplayResponse,
)
from app.repositories.mysql.device_order_repository import DeviceOrderRepository
from app.repositories.mysql.device_repository import DeviceRepository
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository
from app.repositories.mysql.store_menu_repository import StoreMenuRepository
from app.repositories.mysql.visit_session_repository import VisitSessionRepository


class DeviceService:
    """端末から利用するユースケースを実行する。

    Args:
        なし。

    Returns:
        端末用ユースケースを提供するサービス。
    """

    def activate_device(
        self,
        mysql_session: Session,
        activation_code: str,
    ) -> DeviceActivateResponse:
        """端末を初回有効化し、同じトランザクションでコードを消費する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            activation_code: 検証済みの平文の有効化コード。

        Returns:
            登録済み端末のUUIDと新しい端末認証情報。

        Raises:
            DeviceActivationCodeInvalidException: コードで初回有効化できない場合。
        """
        repository = DeviceRepository()
        device = repository.get_device_by_activation_code_hash_for_update(
            mysql_session=mysql_session,
            activation_code_hash=hash_device_secret(activation_code),
        )
        # MySQLのDATETIMEにはタイムゾーン情報を持たないJSTを保存する。
        now = datetime.now(JST).replace(tzinfo=None)
        if (
            device is None
            or device.activation_expires_at is None
            or device.activation_expires_at <= now
            or device.activated_at is not None
            or device.device_credential_hash is not None
        ):
            raise DeviceActivationCodeInvalidException()

        device_credential = secrets.token_urlsafe(32)
        device.device_credential_hash = hash_device_secret(device_credential)
        device.activation_code_hash = None
        device.activation_expires_at = None
        device.activated_at = now
        device.updated_at = now
        device.is_active = True
        repository.save_device(mysql_session=mysql_session, device=device)

        return DeviceActivateResponse(
            device_uuid=device.device_uuid,
            device_credential=device_credential,
        )

    def issue_device_access_token(
        self,
        mysql_session: Session,
        device_uuid: str,
        device_credential: str,
    ) -> DeviceAccessTokenResponse:
        """端末を認証し、アクセストークンを発行して最終認証日時を保存する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 検証済みの端末UUID。
            device_credential: 初回有効化時に発行された端末認証情報。

        Returns:
            端末アクセストークン、トークン種別、有効期間。

        Raises:
            UnauthorizedException: 端末が利用できないか、認証情報が一致しない場合。
        """
        repository = DeviceRepository()
        device = repository.get_device_by_uuid_for_update(
            mysql_session=mysql_session,
            device_uuid=device_uuid,
        )
        if (
            device is None
            or device.activated_at is None
            or not device.is_active
            or device.device_credential_hash is None
            or not secrets.compare_digest(
                hash_device_secret(device_credential),
                device.device_credential_hash,
            )
        ):
            raise UnauthorizedException()

        auth_config = get_device_auth_config()
        access_token = DeviceAuthUtil.create_access_token(
            device_uuid=device.device_uuid,
            config=auth_config,
        )
        # MySQLのDATETIMEにはタイムゾーン情報を持たないJSTを保存する。
        device.last_authenticated_at = datetime.now(JST).replace(tzinfo=None)
        repository.save_device(mysql_session=mysql_session, device=device)

        return DeviceAccessTokenResponse(
            access_token=access_token,
            expires_in=auth_config.access_token_expire_seconds,
        )

    def start_visit_session(
        self,
        mysql_session: Session,
        device_uuid: str,
        start_request_id: str,
    ) -> tuple[int, bool]:
        """端末をロックして来店セッションを開始するか、再送に対応するIDを取得する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 検証済みの端末アクセストークンに含まれるUUID。
            start_request_id: 端末から受け取った開始要求ID。

        Returns:
            来店セッションIDと、新規作成した場合にTrueとなるフラグ。

        Raises:
            UnauthorizedException: 端末が未登録、未有効化、停止、または削除済みの場合。
            VisitSessionConflictException: 開始要求が終了済み、または別セッションが進行中の場合。
        """
        device = DeviceRepository().get_device_by_uuid_for_update(
            mysql_session=mysql_session,
            device_uuid=device_uuid,
        )
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

        repository = VisitSessionRepository()
        existing_session = repository.get_by_start_request_id(
            mysql_session=mysql_session,
            device_id=device.device_id,
            start_request_id=start_request_id,
        )
        if existing_session is not None:
            if existing_session.status == VisitSessionStatus.CLOSED:
                raise VisitSessionConflictException()
            return existing_session.visit_session_id, False

        if repository.has_in_progress_session(mysql_session=mysql_session, device_id=device.device_id):
            raise VisitSessionConflictException()

        visit_session = VisitSession(
            device_id=device.device_id,
            start_request_id=start_request_id,
            status=VisitSessionStatus.ACTIVE,
        )
        saved_visit_session = repository.create_visit_session(
            mysql_session=mysql_session,
            visit_session=visit_session,
        )
        return saved_visit_session.visit_session_id, True

    def complete_visit_session(self, mysql_session: Session, device_uuid: str, visit_session_id: int) -> None:
        """対象セッションをロックし、未払い注文と進行中の決済がなければ終了する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 検証済み端末アクセストークンのUUID。
            visit_session_id: 終了対象の来店セッションID。

        Returns:
            なし。終了済みのセッションへの再送も成功として扱う。

        Raises:
            UnauthorizedException: 端末が未登録、未有効化、停止、または削除済みの場合。
            VisitSessionNotFoundException: 対象が存在しないか、端末にひもづいていない場合。
            VisitSessionCompletionConflictException: 決済処理中、または未払い注文がある場合。
        """
        device = DeviceRepository().get_device_by_uuid_for_update(mysql_session, device_uuid)
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

        visit = VisitSessionRepository().get_visit_session_for_update(mysql_session, device.device_id, visit_session_id)
        if visit is None:
            raise VisitSessionNotFoundException()
        if visit.status == VisitSessionStatus.CLOSED:
            return
        if visit.status == VisitSessionStatus.CHECKOUT_PROCESSING:
            raise VisitSessionCompletionConflictException(DEVICE_CHECKOUT_PROCESSING_ERROR)
        if DeviceOrderRepository().has_unpaid_orders(mysql_session, device.store_id, visit_session_id):
            raise VisitSessionCompletionConflictException(VISIT_SESSION_UNPAID_ORDERS_ERROR)

        visit.status = VisitSessionStatus.CLOSED
        visit.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def get_menu_categories(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
    ) -> DeviceMenuCategoryListResponse:
        """端末と来店セッションの利用可否を確認し、所属店舗のカテゴリーを取得する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 端末が指定した来店セッションID。

        Returns:
            所属店舗の有効・未削除カテゴリーの一覧と画像URL。

        Raises:
            UnauthorizedException: 端末が未登録、未有効化、停止、または削除済みの場合。
            VisitSessionNotFoundException: 端末に紐づく注文受付中のセッションが存在しない場合。
        """
        device = self._get_device_for_active_visit(mysql_session, device_uuid, visit_session_id)
        store_id = device.store_id
        categories = StoreMenuCategoryRepository().get_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
            is_active=True,
        )
        if not categories:
            return DeviceMenuCategoryListResponse(menu_categories=[])

        image_helper = MenuCategoryImageHelper()
        return DeviceMenuCategoryListResponse(
            menu_categories=[
                MenuCategoryDisplayResponse(
                    menu_category_id=category.menu_category_id,
                    name=category.name,
                    image_url=image_helper.generate_presigned_get_url(store_id, category),
                    display_order=category.display_order,
                )
                for category in categories
            ],
        )

    def get_menu_items_by_category(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
        menu_category_id: int,
    ) -> DeviceMenuItemListResponse:
        """指定カテゴリーの販売可能な商品と画像URL、オプションを返す。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 検証済み端末アクセストークンに含まれるUUID。
            visit_session_id: 端末が指定した来店セッションID。
            menu_category_id: 端末が指定したメニューカテゴリーID。

        Returns:
            商品と選択ルールの一覧。有効なカテゴリーに対象商品がなければ空配列。

        Raises:
            UnauthorizedException: 端末を利用できない場合。
            VisitSessionNotFoundException: 端末に紐づく注文受付中のセッションが存在しない場合。
            MenuCategoryNotFoundException: 所属店舗に対象の有効なカテゴリーが存在しない場合。
        """
        device = self._get_device_for_active_visit(mysql_session, device_uuid, visit_session_id)
        rows = StoreMenuRepository().get_menu_items_by_category(
            mysql_session=mysql_session,
            store_id=device.store_id,
            menu_category_id=menu_category_id,
        )
        if not rows:
            raise MenuCategoryNotFoundException()
        if rows[0][1] is None:
            return DeviceMenuItemListResponse(menu_items=[])

        params = SsmClient()
        client = S3Client(s3_endpoint=params.s3_endpoint)
        bucket_name = params.menu_image_bucket
        expires_in = params.menu_image_url_expires_in
        items: dict[int, DeviceMenuItemResponse] = {}
        groups: dict[int, DeviceMenuOptionGroupResponse] = {}
        for _, item, group, option in rows:
            if item is None:
                continue
            if item.menu_item_id not in items:
                key = f"{device.store_id}/{item.menu_item_id}.{item.image_extension}"
                items[item.menu_item_id] = DeviceMenuItemResponse(
                    menu_item_id=item.menu_item_id,
                    name=item.name,
                    price=f"{item.price:.6f}",
                    token_symbol=item.token_symbol,
                    image_url=client.generate_presigned_get_url(
                        bucket_name=bucket_name, file_name=key, expires_in=expires_in,
                    ),
                    display_order=item.display_order,
                    option_groups=[],
                )
            if group is None:
                continue
            if group.menu_option_group_id not in groups:
                group_response = DeviceMenuOptionGroupResponse(
                    menu_option_group_id=group.menu_option_group_id,
                    name=group.name,
                    min_selections=group.min_selections,
                    max_selections=group.max_selections,
                    display_order=group.display_order,
                    options=[],
                )
                groups[group.menu_option_group_id] = group_response
                items[item.menu_item_id].option_groups.append(group_response)
            if option is not None:
                groups[group.menu_option_group_id].options.append(DeviceMenuOptionResponse(
                    menu_option_id=option.menu_option_id,
                    name=option.name,
                    additional_price=f"{option.additional_price:.6f}",
                    display_order=option.display_order,
                ))

        return DeviceMenuItemListResponse(menu_items=list(items.values()))

    def _get_device_for_active_visit(
        self,
        mysql_session: Session,
        device_uuid: str,
        visit_session_id: int,
    ) -> Device:
        """利用可能な端末を取得し、その端末自身の注文受付中セッションを確認する。"""
        device = DeviceRepository().get_device_by_uuid(
            mysql_session=mysql_session,
            device_uuid=device_uuid,
        )
        if device is None or device.activated_at is None or not device.is_active:
            raise UnauthorizedException()

        if not VisitSessionRepository().has_active_visit_session(
            mysql_session=mysql_session,
            device_id=device.device_id,
            visit_session_id=visit_session_id,
        ):
            raise VisitSessionNotFoundException()

        return device
