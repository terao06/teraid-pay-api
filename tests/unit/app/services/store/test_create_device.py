"""デバイス登録Serviceのテスト。"""

import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.core.utils.datetime import JST
from app.models.requests.device_create_request import DeviceCreateRequest
from app.services.store_device_service import (
    ACTIVATION_CODE_VALID_HOURS,
    StoreDeviceService,
)


class TestCreateDevice:
    """StoreDeviceServiceのデバイス登録を検証する。"""

    @patch("app.services.store_device_service.datetime")
    @patch("app.services.store_device_service.secrets.token_urlsafe")
    @patch("app.services.store_device_service.uuid4")
    @patch("app.services.store_device_service.DeviceRepository")
    def test_create_device(
        self,
        mock_repository_class,
        mock_uuid4,
        mock_token_urlsafe,
        mock_datetime,
    ) -> None:
        """UUIDと有効化コードを生成し、ハッシュのみ保存する。"""
        fixed_now = datetime(2026, 11, 16, 10, 0, tzinfo=JST)
        mock_datetime.now.return_value = fixed_now
        mock_uuid4.return_value = "550e8400-e29b-41d4-a716-446655440000"
        mock_token_urlsafe.return_value = "activation-code"
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
        assert saved_device.activation_code_hash == hashlib.sha256(
            b"activation-code"
        ).hexdigest()
        assert saved_device.activation_code_hash != "activation-code"
        assert saved_device.activation_expires_at == fixed_now + timedelta(
            hours=ACTIVATION_CODE_VALID_HOURS
        )
        assert saved_device.is_active is False
        assert result.device_id == 1

