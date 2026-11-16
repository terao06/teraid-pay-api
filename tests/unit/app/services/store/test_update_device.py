"""デバイス更新Serviceのテスト。"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    DeviceActivationStateInvalidException,
    DeviceNotFoundException,
)
from app.models.requests.device_update_request import DeviceUpdateRequest
from app.services.store_device_service import StoreDeviceService


class TestUpdateDevice:
    """StoreDeviceServiceのデバイス更新を検証する。"""

    @patch("app.services.store_device_service.DeviceRepository")
    def test_updates_only_specified_fields(self, mock_repository_class) -> None:
        """指定されたデバイス名だけを更新し、対象行を排他ロックする。"""
        device = SimpleNamespace(
            device_id=1,
            device_name="変更前",
            is_active=False,
            activated_at=None,
            device_credential_hash=None,
        )
        repository = mock_repository_class.return_value
        repository.get_device.return_value = device
        repository.save_device.return_value = device
        mysql_session = Mock()

        result = StoreDeviceService().update_device(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
            request=DeviceUpdateRequest(device_name="  変更後  "),
        )

        assert result is not None
        assert result.device_id == 1
        assert device.device_name == "変更後"
        assert device.is_active is False
        repository.get_device.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
            lock_for_update=True,
        )
        repository.save_device.assert_called_once_with(
            mysql_session=mysql_session,
            device=device,
        )

    @patch("app.services.store_device_service.DeviceRepository")
    def test_allows_reactivating_activated_device(
        self,
        mock_repository_class,
    ) -> None:
        """有効化と端末認証情報の登録が完了した端末は再有効化できる。"""
        device = SimpleNamespace(
            device_id=1,
            device_name="レジ端末1",
            is_active=False,
            activated_at=datetime(2026, 11, 16, 10, 0),
            device_credential_hash="credential-hash",
        )
        repository = mock_repository_class.return_value
        repository.get_device.return_value = device
        repository.save_device.return_value = device

        result = StoreDeviceService().update_device(
            mysql_session=Mock(),
            store_id=101,
            device_id=1,
            request=DeviceUpdateRequest(is_active=True),
        )

        assert result is not None
        assert device.is_active is True

    @patch("app.services.store_device_service.DeviceRepository")
    def test_rejects_activating_unactivated_device(
        self,
        mock_repository_class,
    ) -> None:
        """未有効化端末を管理画面から直接有効化できない。"""
        repository = mock_repository_class.return_value
        repository.get_device.return_value = SimpleNamespace(
            device_id=1,
            device_name="レジ端末1",
            is_active=False,
            activated_at=None,
            device_credential_hash=None,
        )

        with pytest.raises(DeviceActivationStateInvalidException):
            StoreDeviceService().update_device(
                mysql_session=Mock(),
                store_id=101,
                device_id=1,
                request=DeviceUpdateRequest(is_active=True),
            )

        repository.save_device.assert_not_called()

    @patch("app.services.store_device_service.DeviceRepository")
    def test_raises_when_device_does_not_exist(
        self,
        mock_repository_class,
    ) -> None:
        """対象店舗にデバイスが存在しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_device.return_value = None

        with pytest.raises(DeviceNotFoundException):
            StoreDeviceService().update_device(
                mysql_session=Mock(),
                store_id=101,
                device_id=999,
                request=DeviceUpdateRequest(device_name="変更後"),
            )

        mock_repository_class.return_value.save_device.assert_not_called()
