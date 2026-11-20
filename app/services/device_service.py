"""端末の初回有効化とアクセストークン発行の業務処理を提供する。"""

import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config.device_auth import get_device_auth_config
from app.core.exceptions.custom_exception import (
    DeviceActivationCodeInvalidException,
    UnauthorizedException,
)
from app.core.utils.datetime import JST
from app.core.utils.device_activation import hash_device_secret
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.responses.device_access_token_response import DeviceAccessTokenResponse
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
