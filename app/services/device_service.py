"""端末から実行する初回有効化の業務処理を提供する。"""

import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import DeviceActivationCodeInvalidException
from app.core.utils.datetime import JST
from app.core.utils.device_activation import hash_device_secret
from app.models.responses.device_activate_response import DeviceActivateResponse
from app.repositories.mysql.device_repository import DeviceRepository


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
