"""デバイス登録Serviceのテスト。"""

from unittest.mock import Mock, patch

from app.models.requests.device_create_request import DeviceCreateRequest
from app.services.store_device_service import StoreDeviceService


class TestCreateDevice:
    """StoreDeviceServiceのデバイス登録を検証する。"""

    @patch("app.services.store_device_service.uuid4")
    @patch("app.services.store_device_service.DeviceRepository")
    def test_create_device(
        self,
        mock_repository_class,
        mock_uuid4,
    ) -> None:
        """UUIDを生成し、有効化コード未発行の状態で登録する。"""
        mock_uuid4.return_value = "550e8400-e29b-41d4-a716-446655440000"
        mysql_session = Mock()

        def save_device(mysql_session, device):
            """登録対象へ採番済みIDを設定して返す。"""
            device.device_id = 1
            return device

        mock_repository_class.return_value.create_device.side_effect = save_device

        result = StoreDeviceService().create_device(
            mysql_session=mysql_session,
            store_id=101,
            request=DeviceCreateRequest(device_name="  レジ端末1  "),
        )

        saved_device = mock_repository_class.return_value.create_device.call_args.kwargs[
            "device"
        ]
        assert saved_device.store_id == 101
        assert saved_device.device_name == "レジ端末1"
        assert saved_device.device_uuid == "550e8400-e29b-41d4-a716-446655440000"
        assert saved_device.activation_code_hash is None
        assert saved_device.activation_expires_at is None
        assert saved_device.is_active is False
        assert result.device_id == 1

