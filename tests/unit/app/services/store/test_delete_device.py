"""デバイス論理削除Serviceのテスト。"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import DeviceNotFoundException
from app.services.store_device_service import StoreDeviceService


class TestDeleteDevice:
    """対象店舗の未削除デバイスだけを削除する処理を確認する。"""

    @patch("app.services.store_device_service.DeviceRepository")
    def test_locks_and_deletes_device(self, repository_class) -> None:
        """店舗条件で排他ロックしたデバイスを論理削除する。"""
        device = SimpleNamespace(device_id=1)
        repository = repository_class.return_value
        repository.get_device.return_value = device
        session = Mock()

        result = StoreDeviceService().delete_device(session, 101, 1)

        assert result.device_id == 1
        repository.get_device.assert_called_once_with(
            mysql_session=session, store_id=101, device_id=1, lock_for_update=True
        )
        repository.soft_delete_device.assert_called_once_with(
            mysql_session=session, device=device
        )

    @patch("app.services.store_device_service.DeviceRepository")
    def test_missing_device_does_not_write(self, repository_class) -> None:
        """対象がない場合は例外を送出して更新しない。"""
        repository = repository_class.return_value
        repository.get_device.return_value = None

        with pytest.raises(DeviceNotFoundException):
            StoreDeviceService().delete_device(Mock(), 101, 1)

        repository.soft_delete_device.assert_not_called()
