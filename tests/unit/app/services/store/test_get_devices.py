"""デバイス一覧取得Serviceのテスト。"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.utils.datetime import JST
from app.services.store_device_service import StoreDeviceService


class TestGetDevices:
    """StoreDeviceServiceのデバイス一覧取得を検証する。"""

    @patch("app.services.store_device_service.DeviceRepository")
    def test_returns_devices_and_pagination(self, mock_repository_class) -> None:
        """検索条件とページ指定をRepositoryへ渡し、指定項目だけを返す。"""
        repository = mock_repository_class.return_value
        repository.count_devices.return_value = 3
        repository.get_devices.return_value = [
            SimpleNamespace(
                device_id=12,
                device_name="レジ端末2",
                is_active=True,
                created_at=datetime(2026, 11, 16, 10, 0),
                device_uuid="responseに含めない",
            )
        ]
        mysql_session = Mock()

        result = StoreDeviceService().get_devices(
            mysql_session=mysql_session,
            store_id=101,
            device_name="レジ",
            is_active=True,
            page=2,
            page_size=2,
        )

        assert result.model_dump() == {
            "devices": [
                {
                    "device_id": 12,
                    "device_name": "レジ端末2",
                    "is_active": True,
                    "created_at": datetime(2026, 11, 16, 10, 0, tzinfo=JST),
                }
            ],
            "pagination": {
                "page": 2,
                "page_size": 2,
                "total": 3,
                "total_pages": 2,
            },
        }
        repository.get_devices.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            device_name="レジ",
            is_active=True,
            offset=2,
            limit=2,
        )

    @patch("app.services.store_device_service.DeviceRepository")
    def test_returns_empty_list_without_fetching_rows(
        self,
        mock_repository_class,
    ) -> None:
        """該当件数が0件の場合は明細を検索せず空の一覧を返す。"""
        repository = mock_repository_class.return_value
        repository.count_devices.return_value = 0

        result = StoreDeviceService().get_devices(
            mysql_session=Mock(),
            store_id=101,
        )

        assert result.devices == []
        assert result.pagination.total == 0
        assert result.pagination.total_pages == 0
        repository.get_devices.assert_not_called()
