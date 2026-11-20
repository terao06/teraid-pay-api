"""端末初回有効化Serviceの業務ルールを検証する。"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import DeviceActivationCodeInvalidException
from app.core.utils.datetime import JST
from app.models.mysql.device import Device
from app.services.device_service import DeviceService


ACTIVATION_CODE = "ABCD-EFGH-JKLM"
NOW = datetime(2026, 11, 20, 12, tzinfo=JST)


class TestActivateDevice:
    """有効化前のチェックと端末状態の更新を確認する。"""

    @patch("app.services.device_service.datetime")
    @patch("app.services.device_service.DeviceRepository")
    def test_activates_device_with_valid_code(self, repository_class, clock) -> None:
        """検索後の時刻で期限を判定し、認証情報のハッシュと新しい状態を保存する。"""
        mysql_session = Mock()
        device = Device(
            device_uuid="device-uuid",
            activation_code_hash=hashlib.sha256(ACTIVATION_CODE.encode()).hexdigest(),
            activation_expires_at=NOW.replace(tzinfo=None) + timedelta(minutes=1),
            is_active=False,
        )
        repository = repository_class.return_value

        def return_locked_device(**kwargs) -> Device:
            """ロックを取得した直後に判定時刻を参照できるようにする。"""
            clock.now.assert_not_called()
            clock.now.return_value = NOW
            return device

        repository.get_device_by_activation_code_hash_for_update.side_effect = return_locked_device

        result = DeviceService().activate_device(mysql_session, ACTIVATION_CODE)

        clock.now.assert_called_once_with(JST)
        repository.get_device_by_activation_code_hash_for_update.assert_called_once_with(
            mysql_session=mysql_session,
            activation_code_hash=hashlib.sha256(ACTIVATION_CODE.encode()).hexdigest(),
        )
        repository.save_device.assert_called_once_with(mysql_session=mysql_session, device=device)
        assert result.device_uuid == device.device_uuid
        assert device.device_credential_hash == hashlib.sha256(
            result.device_credential.encode()
        ).hexdigest()
        assert device.is_active is True
        assert device.activated_at == device.updated_at == NOW.replace(tzinfo=None)
        assert device.activation_code_hash is None
        assert device.activation_expires_at is None

    @pytest.mark.parametrize(
        ("expires_at", "activated_at", "credential_hash"),
        [
            (None, None, None),
            (NOW.replace(tzinfo=None), None, None),
            (NOW.replace(tzinfo=None) - timedelta(seconds=1), None, None),
            (NOW.replace(tzinfo=None) + timedelta(minutes=1), NOW.replace(tzinfo=None), None),
            (NOW.replace(tzinfo=None) + timedelta(minutes=1), None, "credential-hash"),
        ],
    )
    @patch("app.services.device_service.datetime")
    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_invalid_device_state(
        self,
        repository_class,
        clock,
        expires_at,
        activated_at,
        credential_hash,
    ) -> None:
        """期限なし、期限到達、有効化済み、認証情報登録済みの端末を更新しない。"""
        clock.now.return_value = NOW
        repository = repository_class.return_value
        repository.get_device_by_activation_code_hash_for_update.return_value = Device(
            activation_expires_at=expires_at,
            activated_at=activated_at,
            device_credential_hash=credential_hash,
        )

        with pytest.raises(DeviceActivationCodeInvalidException):
            DeviceService().activate_device(Mock(), ACTIVATION_CODE)

        repository.save_device.assert_not_called()

    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_unknown_code(self, repository_class) -> None:
        """一致する端末がなければ認証情報を作成せず例外を送出する。"""
        repository = repository_class.return_value
        repository.get_device_by_activation_code_hash_for_update.return_value = None

        with pytest.raises(DeviceActivationCodeInvalidException):
            DeviceService().activate_device(Mock(), ACTIVATION_CODE)

        repository.save_device.assert_not_called()
