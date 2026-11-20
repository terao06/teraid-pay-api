"""端末アクセストークンの設定とJWT発行を検証する。"""

from unittest.mock import patch

import jwt
import pytest

from app.core.config.device_auth import DeviceAuthConfig, get_device_auth_config
from app.core.utils.device_auth import DeviceAuthUtil


DEVICE_UUID = "81005100-0000-4000-8000-000000000051"
JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"


class TestDeviceAuthConfig:
    """端末用署名鍵と有効期間の取得を確認する。"""

    @pytest.mark.parametrize(("overrides", "expires_in"), [({}, 300), ({"device_jwt_expire_seconds": 120}, 120)])
    @patch("app.core.config.device_auth.SecretManager")
    def test_loads_device_auth_settings(self, secret_manager, overrides, expires_in) -> None:
        """端末用の鍵と指定または既定の有効期間を読み込む。"""
        get_secret = secret_manager.return_value.get_secret
        get_secret.return_value = {"device_jwt_secret": JWT_SECRET, **overrides}

        config = get_device_auth_config()

        get_secret.assert_called_once_with("secret")
        assert config.jwt_secret == JWT_SECRET
        assert config.access_token_expire_seconds == expires_in

    @pytest.mark.parametrize(
        "secret",
        [
            "invalid-json",
            {"store_manager_jwt_secret": JWT_SECRET},
            {"device_jwt_secret": "short"},
            {"device_jwt_secret": JWT_SECRET, "device_jwt_expire_seconds": 0},
            {"device_jwt_secret": JWT_SECRET, "device_jwt_expire_seconds": "invalid"},
        ],
    )
    @patch("app.core.config.device_auth.SecretManager")
    def test_rejects_invalid_settings(self, secret_manager, secret) -> None:
        """端末用の署名鍵や有効期間が不正な場合は例外を送出する。"""
        secret_manager.return_value.get_secret.return_value = secret

        with pytest.raises(ValueError):
            get_device_auth_config()


class TestDeviceAuthUtil:
    """署名付きJWTに含まれる端末情報と有効期限を確認する。"""

    def test_create_access_token(self) -> None:
        """端末UUID、有効期限、一意なIDを持つJWTを作成する。"""
        config = DeviceAuthConfig(jwt_secret=JWT_SECRET, access_token_expire_seconds=300)

        token = DeviceAuthUtil.create_access_token(device_uuid=DEVICE_UUID, config=config)

        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == payload["device_uuid"] == DEVICE_UUID
        assert payload["exp"] - payload["iat"] == 300
        assert payload["jti"]
