"""端末アクセストークンの署名鍵と有効期間の設定を提供する。"""

from dataclasses import dataclass, field

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class DeviceAuthConfig:
    """端末アクセストークンの発行設定を保持する。

    Args:
        jwt_secret: 端末アクセストークンのJWT署名鍵。
        access_token_expire_seconds: アクセストークンの有効期間（秒）。

    Returns:
        端末認証の設定。
    """

    jwt_secret: str = field(repr=False)
    access_token_expire_seconds: int


def get_device_auth_config() -> DeviceAuthConfig:
    """Secrets Managerから端末認証の設定を取得する。

    Args:
        なし。

    Returns:
        端末用のJWT署名鍵と有効期間。有効期間の既定値は300秒。

    Raises:
        ValueError: シークレットの形式、署名鍵、または有効期間の設定が不正な場合。
    """
    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets Manager の secret は JSON 形式である必要があります。")

    jwt_secret = secret.get("device_jwt_secret")
    if not isinstance(jwt_secret, str) or len(jwt_secret) < 32:
        raise ValueError(
            "secret に32文字以上の device_jwt_secret を設定してください。"
        )

    expire_value = secret.get("device_jwt_expire_seconds", 300)
    try:
        access_token_expire_seconds = int(expire_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "device_jwt_expire_seconds は整数で設定してください。"
        ) from error

    if access_token_expire_seconds <= 0:
        raise ValueError(
            "device_jwt_expire_seconds は1以上で設定してください。"
        )

    return DeviceAuthConfig(
        jwt_secret=jwt_secret,
        access_token_expire_seconds=access_token_expire_seconds,
    )
