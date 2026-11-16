"""デバイス有効化コード発行Serviceのテスト。"""

import base64
import hashlib
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    DeviceAlreadyActivatedException,
    DeviceNotFoundException,
)
from app.core.utils.datetime import JST
from app.services.store_device_service import (
    ACTIVATION_CODE_VALID_HOURS,
    StoreDeviceService,
)


class TestIssueDeviceActivationCode:
    """StoreDeviceServiceの有効化コード発行を検証する。"""

    @patch("app.services.store_device_service.datetime")
    @patch.object(StoreDeviceService, "_generate_qr_code_image")
    @patch.object(StoreDeviceService, "_generate_activation_code")
    @patch("app.services.store_device_service.DeviceRepository")
    def test_issues_code_and_replaces_existing_code(
        self,
        mock_repository_class,
        mock_generate_code,
        mock_generate_qr_code,
        mock_datetime,
    ) -> None:
        """既存コードを最新コードのハッシュと有効期限で上書きする。"""
        fixed_now = datetime(2026, 11, 17, 10, 0, tzinfo=JST)
        mock_datetime.now.return_value = fixed_now
        mock_generate_code.return_value = "ABCD-EFGH-JKLM"
        mock_generate_qr_code.return_value = "data:image/png;base64,cG5n"
        device = SimpleNamespace(
            device_id=1,
            activated_at=None,
            device_credential_hash=None,
            activation_code_hash="old-hash",
            activation_expires_at=datetime(2026, 11, 17, 9, 0, tzinfo=JST),
        )
        repository = mock_repository_class.return_value
        repository.get_device.return_value = device
        repository.save_device.return_value = device
        mysql_session = Mock()

        result = StoreDeviceService().issue_activation_code(
            mysql_session=mysql_session,
            store_id=101,
            device_id=1,
        )

        expected_expires_at = fixed_now + timedelta(
            hours=ACTIVATION_CODE_VALID_HOURS
        )
        assert result.device_id == 1
        assert result.activation_code == "ABCD-EFGH-JKLM"
        assert result.qr_code_image == "data:image/png;base64,cG5n"
        assert result.activation_expires_at == expected_expires_at
        assert device.activation_code_hash == hashlib.sha256(
            b"ABCD-EFGH-JKLM"
        ).hexdigest()
        assert device.activation_expires_at == expected_expires_at
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
        mock_generate_qr_code.assert_called_once_with("ABCD-EFGH-JKLM")

    @patch("app.services.store_device_service.DeviceRepository")
    def test_raises_when_device_does_not_exist(
        self,
        mock_repository_class,
    ) -> None:
        """対象店舗にデバイスが存在しない場合は専用例外を送出する。"""
        mock_repository_class.return_value.get_device.return_value = None

        with pytest.raises(DeviceNotFoundException):
            StoreDeviceService().issue_activation_code(
                mysql_session=Mock(),
                store_id=101,
                device_id=999,
            )

    @pytest.mark.parametrize(
        ("activated_at", "credential_hash"),
        [
            (datetime(2026, 11, 17, 10, 0), None),
            (None, "credential-hash"),
        ],
    )
    @patch("app.services.store_device_service.DeviceRepository")
    def test_rejects_activated_device(
        self,
        mock_repository_class,
        activated_at,
        credential_hash,
    ) -> None:
        """有効化済みまたは端末認証情報登録済みのデバイスには発行しない。"""
        repository = mock_repository_class.return_value
        repository.get_device.return_value = SimpleNamespace(
            device_id=1,
            activated_at=activated_at,
            device_credential_hash=credential_hash,
        )

        with pytest.raises(DeviceAlreadyActivatedException):
            StoreDeviceService().issue_activation_code(
                mysql_session=Mock(),
                store_id=101,
                device_id=1,
            )

        repository.save_device.assert_not_called()

    @patch("app.services.store_device_service.secrets.choice")
    def test_generates_human_readable_code(self, mock_choice) -> None:
        """曖昧文字を除いた12文字を4文字単位で区切って生成する。"""
        mock_choice.side_effect = list("ABCDEFGHJKLM")

        result = StoreDeviceService._generate_activation_code()

        assert result == "ABCD-EFGH-JKLM"

    def test_generates_png_qr_code_in_memory(self) -> None:
        """有効化コードから保存不要なPNG形式のQR画像を生成する。"""
        result = StoreDeviceService._generate_qr_code_image("ABCD-EFGH-JKLM")

        prefix = "data:image/png;base64,"
        assert result.startswith(prefix)
        image_data = base64.b64decode(result.removeprefix(prefix))
        assert image_data.startswith(b"\x89PNG\r\n\x1a\n")

    def test_qr_payload_does_not_include_api_url(self) -> None:
        """QR格納内容にはAPI URLを含めず、固定形式とコードだけを含める。"""
        result = StoreDeviceService._build_activation_qr_payload(
            "ABCD-EFGH-JKLM"
        )

        assert json.loads(result) == {
            "type": "teraid_pay_device_activation",
            "version": 1,
            "activation_code": "ABCD-EFGH-JKLM",
        }
        assert "http://" not in result
        assert "https://" not in result
