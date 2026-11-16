"""店舗管理者によるデバイス管理ユースケースを提供する。"""

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from io import BytesIO
from uuid import uuid4

import qrcode
from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.core.exceptions.custom_exception import (
    DeviceActivationStateInvalidException,
    DeviceAlreadyActivatedException,
    DeviceNotFoundException,
)
from app.models.mysql.device import Device
from app.models.requests.device_create_request import DeviceCreateRequest
from app.models.requests.device_update_request import DeviceUpdateRequest
from app.models.responses.device_create_response import DeviceCreateResponse
from app.models.responses.device_activation_code_response import (
    DeviceActivationCodeResponse,
)
from app.models.responses.device_detail_response import DeviceDetailResponse
from app.models.responses.device_list_response import (
    DeviceListItemResponse,
    DeviceListResponse,
    DevicePaginationResponse,
)
from app.models.responses.device_update_response import DeviceUpdateResponse
from app.repositories.mysql.device_repository import DeviceRepository


ACTIVATION_CODE_VALID_HOURS = 24
ACTIVATION_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ACTIVATION_CODE_LENGTH = 12
ACTIVATION_CODE_GROUP_SIZE = 4


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
        """デバイスUUIDを発行し、コード未発行の状態で登録する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            request: デバイス名を含む登録リクエスト。

        Returns:
            登録したデバイスID。
        """
        device = Device(
            store_id=store_id,
            device_name=request.device_name,
            device_uuid=str(uuid4()),
            activation_code_hash=None,
            activation_expires_at=None,
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

    def issue_activation_code(
        self,
        mysql_session: Session,
        store_id: int,
        device_id: int,
    ) -> DeviceActivationCodeResponse:
        """未有効化デバイスへ新しい有効化コードを発行する。

        既存コードがある場合も同じ項目を上書きし、最新コードだけを有効にする。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            device_id: 有効化コードを発行するデバイスID。

        Returns:
            平文の有効化コードと有効期限。

        Raises:
            DeviceNotFoundException: 対象デバイスが存在しない場合。
            DeviceAlreadyActivatedException: 対象デバイスが有効化済みの場合。
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
        if device.activated_at is not None or device.device_credential_hash:
            raise DeviceAlreadyActivatedException()

        activation_code = self._generate_activation_code()
        activation_expires_at = datetime.now(JST) + timedelta(
            hours=ACTIVATION_CODE_VALID_HOURS
        )
        device.activation_code_hash = self._hash_activation_code(activation_code)
        device.activation_expires_at = activation_expires_at
        saved_device = repository.save_device(
            mysql_session=mysql_session,
            device=device,
        )
        return DeviceActivationCodeResponse(
            device_id=saved_device.device_id,
            activation_code=activation_code,
            qr_code_image=self._generate_qr_code_image(activation_code),
            activation_expires_at=activation_expires_at,
        )

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
    def _generate_activation_code() -> str:
        """手入力しやすく推測困難な有効化コードを生成する。

        Returns:
            4文字単位をハイフンで区切った12文字の有効化コード。
        """
        raw_code = "".join(
            secrets.choice(ACTIVATION_CODE_ALPHABET)
            for _ in range(ACTIVATION_CODE_LENGTH)
        )
        return "-".join(
            raw_code[index : index + ACTIVATION_CODE_GROUP_SIZE]
            for index in range(0, ACTIVATION_CODE_LENGTH, ACTIVATION_CODE_GROUP_SIZE)
        )

    @staticmethod
    def _generate_qr_code_image(activation_code: str) -> str:
        """有効化情報を格納したQRコードPNGをメモリ上で生成する。

        QRコードにはAPI URLを含めず、端末アプリが解釈する固定形式のJSONを
        格納する。

        Args:
            activation_code: 平文の有効化コード。

        Returns:
            Base64形式のPNG画像を含むdata URL。
        """
        payload = StoreDeviceService._build_activation_qr_payload(activation_code)
        qr_code = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr_code.add_data(payload)
        qr_code.make(fit=True)
        image = qr_code.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        encoded_image = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded_image}"

    @staticmethod
    def _build_activation_qr_payload(activation_code: str) -> str:
        """端末アプリが解釈する有効化用QR格納文字列を生成する。

        API URLは端末アプリ側の設定を使用するため、格納文字列には含めない。

        Args:
            activation_code: 平文の有効化コード。

        Returns:
            形式識別子、バージョン、有効化コードを含むJSON文字列。
        """
        return json.dumps(
            {
                "type": "teraid_pay_device_activation",
                "version": 1,
                "activation_code": activation_code,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

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
