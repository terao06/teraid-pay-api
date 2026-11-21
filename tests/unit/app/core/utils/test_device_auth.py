"""端末アクセストークンの設定、JWTの発行と検証を確認する。"""

from datetime import datetime, timezone
from unittest.mock import patch

import jwt
import pytest

from app.core.config.device_auth import DeviceAuthConfig, get_device_auth_config
from app.core.exceptions.custom_exception import UnauthorizedException
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
    """署名付きJWTの発行と端末UUIDを取得する条件を確認する。"""

    def test_create_access_token(self) -> None:
        """端末UUID、有効期限、一意なIDを持つJWTを作成する。"""
        config = DeviceAuthConfig(jwt_secret=JWT_SECRET, access_token_expire_seconds=300)

        token = DeviceAuthUtil.create_access_token(device_uuid=DEVICE_UUID, config=config)

        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == payload["device_uuid"] == DEVICE_UUID
        assert payload["exp"] - payload["iat"] == 300
        assert payload["jti"]


    def test_verifies_issued_access_token(self) -> None:
        """既存の発行処理で署名したJWTから端末UUIDを取得する。

        Args:
            なし。

        Returns:
            なし。
        """
        config = DeviceAuthConfig(jwt_secret=JWT_SECRET, access_token_expire_seconds=300)
        token = DeviceAuthUtil.create_access_token(DEVICE_UUID, config)

        assert DeviceAuthUtil.verify_access_token(token, config) == DEVICE_UUID

    @pytest.mark.parametrize(
        ("overrides", "signing_key"),
        [
            ({"exp": None}, JWT_SECRET),
            ({"exp": 1}, JWT_SECRET),
            ({"device_uuid": None}, JWT_SECRET),
            ({"device_uuid": "invalid", "sub": "invalid"}, JWT_SECRET),
            ({"sub": "different"}, JWT_SECRET),
            ({}, "wrong-signing-secret-at-least-32-characters"),
        ],
    )
    def test_rejects_invalid_access_token(self, overrides, signing_key) -> None:
        """必須クレーム、期限、署名のいずれかが不正な端末JWTを拒否する。

        Args:
            overrides: 通常のJWTクレームに適用する不正値。
            signing_key: JWTの署名に使う鍵。

        Returns:
            なし。
        """
        config = DeviceAuthConfig(jwt_secret=JWT_SECRET, access_token_expire_seconds=300)
        payload = {
            "sub": DEVICE_UUID,
            "device_uuid": DEVICE_UUID,
            "exp": int(datetime.now(timezone.utc).timestamp()) + 300,
            **overrides,
        }
        token = jwt.encode(payload, signing_key, algorithm="HS256")

        with pytest.raises(UnauthorizedException):
            DeviceAuthUtil.verify_access_token(token, config)
