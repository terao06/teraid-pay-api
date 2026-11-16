"""店舗管理者によるデバイス管理ユースケースを提供する。"""

import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.core.exceptions.custom_exception import (
    DeviceActivationStateInvalidException,
    DeviceNotFoundException,
)
from app.models.mysql.device import Device
from app.models.requests.device_create_request import DeviceCreateRequest
from app.models.requests.device_update_request import DeviceUpdateRequest
from app.models.responses.device_create_response import DeviceCreateResponse
from app.models.responses.device_detail_response import DeviceDetailResponse
from app.models.responses.device_list_response import (
    DeviceListItemResponse,
    DeviceListResponse,
    DevicePaginationResponse,
)
from app.models.responses.device_update_response import DeviceUpdateResponse
from app.repositories.mysql.device_repository import DeviceRepository


ACTIVATION_CODE_VALID_HOURS = 24
ACTIVATION_CODE_BYTES = 18


class StoreDeviceService:
    """店舗に紐付くデバイスの登録・参照・更新を調停する。

    Returns:
        店舗管理者向けデバイス管理ユースケースを提供するサービス。
    """

    def create_device(
        self,
        mysql_session: Session,
        store_id: int,
        request: DeviceCreateRequest,
    ) -> DeviceCreateResponse:
        """デバイスUUIDと有効化コードを発行して登録する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            request: デバイス名を含む登録リクエスト。

        Returns:
            登録したデバイスID。
        """
        device_uuid = str(uuid4())
        activation_code = secrets.token_urlsafe(ACTIVATION_CODE_BYTES)
        activation_expires_at = datetime.now(JST) + timedelta(
            hours=ACTIVATION_CODE_VALID_HOURS
        )
        device = Device(
            store_id=store_id,
            device_name=request.device_name,
            device_uuid=device_uuid,
            activation_code_hash=self._hash_activation_code(activation_code),
            activation_expires_at=activation_expires_at,
            is_active=False,
        )
        saved_device = DeviceRepository().create_device(
            mysql_session=mysql_session,
            device=device,
        )
        return DeviceCreateResponse(
            device_id=saved_device.device_id,
        )

    def get_devices(
        self,
        mysql_session: Session,
        store_id: int,
        device_name: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DeviceListResponse:
        """店舗に紐づくデバイスを検索条件とページ指定に従って取得する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            device_name: デバイス名の部分一致条件。
            is_active: 利用可能状態の完全一致条件。
            page: 取得するページ番号。
            page_size: 1ページあたりの取得件数。

        Returns:
            デバイス一覧とページネーション情報。
        """
        repository = DeviceRepository()
        total = repository.count_devices(
            mysql_session=mysql_session,
            store_id=store_id,
            device_name=device_name,
            is_active=is_active,
        )
        pagination = DevicePaginationResponse(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )
        if total == 0:
            return DeviceListResponse(devices=[], pagination=pagination)

        devices = repository.get_devices(
            mysql_session=mysql_session,
            store_id=store_id,
            device_name=device_name,
            is_active=is_active,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return DeviceListResponse(
            devices=[
                DeviceListItemResponse(
                    device_id=device.device_id,
                    device_name=device.device_name,
                    is_active=device.is_active,
                    created_at=self._as_jst(device.created_at),
                )
                for device in devices
            ],
            pagination=pagination,
        )

    def get_device_detail(
        self,
        mysql_session: Session,
        store_id: int,
        device_id: int,
    ) -> DeviceDetailResponse:
        """店舗に属するデバイスの管理画面向け詳細情報を取得する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            device_id: 取得対象のデバイスID。

        Returns:
            管理画面へ表示可能なデバイス詳細情報。

        Raises:
            DeviceNotFoundException: 対象デバイスが存在しない場合。
        """
        device = DeviceRepository().get_device(
            mysql_session=mysql_session,
            store_id=store_id,
            device_id=device_id,
        )
        if device is None:
            raise DeviceNotFoundException()
        return DeviceDetailResponse(
            device_id=device.device_id,
            device_name=device.device_name,
            is_active=device.is_active,
            activated_at=(
                self._as_jst(device.activated_at)
                if device.activated_at is not None
                else None
            ),
            last_authenticated_at=(
                self._as_jst(device.last_authenticated_at)
                if device.last_authenticated_at is not None
                else None
            ),
            created_at=self._as_jst(device.created_at),
            updated_at=self._as_jst(device.updated_at),
        )

    def update_device(
        self,
        mysql_session: Session,
        store_id: int,
        device_id: int,
        request: DeviceUpdateRequest,
    ) -> DeviceUpdateResponse:
        """店舗に属するデバイス名または利用状態を更新する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            device_id: 更新対象のデバイスID。
            request: デバイス名または利用状態を含む更新リクエスト。

        Returns:
            更新したデバイスID。

        Raises:
            DeviceNotFoundException: 対象デバイスが存在しない場合。
            DeviceActivationStateInvalidException: 未有効化デバイスを
                利用可能に変更しようとした場合。
        """
        repository = DeviceRepository()
        device = repository.get_device(
            mysql_session=mysql_session,
            store_id=store_id,
            device_id=device_id,
            lock_for_update=True,
        )
        if device is None:
            raise DeviceNotFoundException()
        if request.is_active is True and (
            device.activated_at is None or not device.device_credential_hash
        ):
            raise DeviceActivationStateInvalidException()
        if "device_name" in request.model_fields_set:
            device.device_name = request.device_name
        if "is_active" in request.model_fields_set:
            device.is_active = request.is_active
        saved_device = repository.save_device(
            mysql_session=mysql_session,
            device=device,
        )
        return DeviceUpdateResponse(device_id=saved_device.device_id)

    @staticmethod
    def _hash_activation_code(activation_code: str) -> str:
        """有効化コードをDB保存用のSHA-256ハッシュへ変換する。

        Args:
            activation_code: 平文の有効化コード。

        Returns:
            16進64文字のSHA-256ハッシュ。
        """
        return hashlib.sha256(activation_code.encode("utf-8")).hexdigest()

    @staticmethod
    def _as_jst(value: datetime) -> datetime:
        """DBから取得した日時をJSTのタイムゾーン付き日時へ変換する。

        Args:
            value: DBから取得した日時。

        Returns:
            JSTのタイムゾーン情報を持つ日時。
        """
        if value.tzinfo is None:
            return value.replace(tzinfo=JST)
        return value.astimezone(JST)
