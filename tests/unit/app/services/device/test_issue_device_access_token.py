"""端末アクセストークン発行Serviceの業務ルールを検証する。"""

import hashlib
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.custom_exception import UnauthorizedException
from app.core.utils.datetime import JST
from app.models.mysql.device import Device
from app.services.device_service import DeviceService


DEVICE_UUID = "81005100-0000-4000-8000-000000000051"
DEVICE_CREDENTIAL = "test-device-access-credential"
CREDENTIAL_HASH = hashlib.sha256(DEVICE_CREDENTIAL.encode()).hexdigest()
NOW = datetime(2026, 11, 20, 12, tzinfo=JST)
ACTIVATED_AT = datetime(2026, 11, 20, 11)


class TestIssueDeviceAccessToken:
    """端末状態と認証情報の照合、発行後の日時更新を確認する。"""

    @patch("app.services.device_service.datetime")
    @patch("app.services.device_service.DeviceAuthUtil")
    @patch("app.services.device_service.get_device_auth_config")
    @patch("app.services.device_service.DeviceRepository")
    def test_issues_token_and_updates_last_authenticated_at(
        self, repository_class, get_device_auth_config, auth_util, clock,
    ) -> None:
        """利用可能な端末にトークンを発行し、最終認証日時を保存する。"""
        mysql_session = Mock()
        device = Device(
            device_uuid=DEVICE_UUID,
            activated_at=ACTIVATED_AT,
            is_active=True,
            device_credential_hash=CREDENTIAL_HASH,
        )
        repository = repository_class.return_value
        repository.get_device_by_uuid_for_update.return_value = device
        config = DeviceAuthConfig(
            jwt_secret="test-device-jwt-secret-at-least-32-characters",
            access_token_expire_seconds=120,
        )
        get_device_auth_config.return_value = config
        auth_util.create_access_token.return_value = "test-access-token"
        clock.now.return_value = NOW

        result = DeviceService().issue_device_access_token(
            mysql_session, DEVICE_UUID, DEVICE_CREDENTIAL,
        )

        repository.get_device_by_uuid_for_update.assert_called_once_with(
            mysql_session=mysql_session, device_uuid=DEVICE_UUID,
        )
        auth_util.create_access_token.assert_called_once_with(device_uuid=DEVICE_UUID, config=config)
        clock.now.assert_called_once_with(JST)
        repository.save_device.assert_called_once_with(mysql_session=mysql_session, device=device)
        assert device.last_authenticated_at == NOW.replace(tzinfo=None)
        assert device.device_credential_hash == CREDENTIAL_HASH
        assert result.access_token == "test-access-token"
        assert result.token_type == "Bearer"
        assert result.expires_in == 120

    @pytest.mark.parametrize(
        "device",
        [
            None,
            Device(activated_at=None, is_active=True, device_credential_hash=CREDENTIAL_HASH),
            Device(activated_at=ACTIVATED_AT, is_active=False, device_credential_hash=CREDENTIAL_HASH),
            Device(activated_at=ACTIVATED_AT, is_active=True, device_credential_hash=None),
            Device(activated_at=ACTIVATED_AT, is_active=True, device_credential_hash="wrong-hash"),
        ],
    )
    @patch("app.services.device_service.get_device_auth_config")
    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_unavailable_device(
        self, repository_class, get_device_auth_config, device,
    ) -> None:
        """対象なし、利用不可、または認証情報が不正な端末には発行しない。"""
        repository = repository_class.return_value
        repository.get_device_by_uuid_for_update.return_value = device

        with pytest.raises(UnauthorizedException):
            DeviceService().issue_device_access_token(Mock(), DEVICE_UUID, DEVICE_CREDENTIAL)

        get_device_auth_config.assert_not_called()
        repository.save_device.assert_not_called()

    @patch("app.services.device_service.DeviceAuthUtil")
    @patch("app.services.device_service.get_device_auth_config")
    @patch("app.services.device_service.DeviceRepository")
    def test_does_not_update_timestamp_on_signing_failure(
        self, repository_class, get_device_auth_config, auth_util,
    ) -> None:
        """署名に失敗したときは最終認証日時を更新しない。"""
        repository = repository_class.return_value
        device = Device(
            activated_at=ACTIVATED_AT,
            is_active=True,
            device_credential_hash=CREDENTIAL_HASH,
        )
        repository.get_device_by_uuid_for_update.return_value = device
        auth_util.create_access_token.side_effect = RuntimeError("signing failed")

        with pytest.raises(RuntimeError, match="signing failed"):
            DeviceService().issue_device_access_token(Mock(), DEVICE_UUID, DEVICE_CREDENTIAL)

        get_device_auth_config.assert_called_once_with()
        repository.save_device.assert_not_called()
        assert device.last_authenticated_at is None
