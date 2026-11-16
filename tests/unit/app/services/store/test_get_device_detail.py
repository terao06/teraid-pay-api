"""デバイス詳細取得Serviceのテスト。"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import DeviceNotFoundException
from app.core.utils.datetime import JST
from app.services.store_device_service import StoreDeviceService


class TestGetDeviceDetail:
    """StoreDeviceServiceのデバイス詳細取得を検証する。"""

    @patch("app.services.store_device_service.DeviceRepository")
    def test_returns_only_displayable_fields(self, mock_repository_class) -> None:
        """DBの認証情報を除外し、管理画面表示項目だけを返す。"""
        mock_repository_class.return_value.get_device.return_value = SimpleNamespace(
            device_id=1,
            device_name="レジ端末1",
            is_active=True,
            activated_at=datetime(2026, 11, 16, 9, 0),
            last_authenticated_at=datetime(2026, 11, 16, 10, 0, tzinfo=JST),
            created_at=datetime(2026, 11, 15, 10, 0),
            updated_at=datetime(2026, 11, 16, 10, 0),
            device_uuid="responseに含めない",
            activation_code_hash="responseに含めない",
            device_credential_hash="responseに含めない",
        )
        mysql_session = Mock()

        result = StoreDeviceService().get_device_detail(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

        assert result is not None
        assert result.model_dump() == {
            "device_id": 1,
            "device_name": "レジ端末1",
            "is_active": True,
            "activated_at": datetime(2026, 11, 16, 9, 0, tzinfo=JST),
            "last_authenticated_at": datetime(2026, 11, 16, 10, 0, tzinfo=JST),
            "created_at": datetime(2026, 11, 15, 10, 0, tzinfo=JST),
            "updated_at": datetime(2026, 11, 16, 10, 0, tzinfo=JST),
        }
        mock_repository_class.return_value.get_device.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

    @patch("app.services.store_device_service.DeviceRepository")
    def test_raises_when_device_does_not_exist(
        self,
        mock_repository_class,
    ) -> None:
        """対象店舗にデバイスが存在しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_device.return_value = None

        with pytest.raises(DeviceNotFoundException):
            StoreDeviceService().get_device_detail(
                mysql_session=Mock(),
                store_id=101,
                device_id=999,
            )
