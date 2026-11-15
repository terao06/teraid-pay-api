from dataclasses import dataclass

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class StoreManagerAuthConfig:
    """店舗管理者認証に使用する設定。"""

    jwt_secret: str
    access_token_expire_seconds: int


def get_store_manager_auth_config() -> StoreManagerAuthConfig:
    """Secrets Manager から店舗管理者認証設定を取得する。"""
    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets Manager の secret は JSON 形式である必要があります。")

    jwt_secret = secret.get("store_manager_jwt_secret")
    if not isinstance(jwt_secret, str) or len(jwt_secret) < 32:
        raise ValueError(
            "secret に32文字以上の store_manager_jwt_secret を設定してください。"
        )

    expire_value = secret.get("store_manager_jwt_expire_seconds", 3600)
    try:
        access_token_expire_seconds = int(expire_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "store_manager_jwt_expire_seconds は整数で設定してください。"
        ) from error

    if access_token_expire_seconds <= 0:
        raise ValueError(
            "store_manager_jwt_expire_seconds は1以上で設定してください。"
        )

    return StoreManagerAuthConfig(
        jwt_secret=jwt_secret,
        access_token_expire_seconds=access_token_expire_seconds,
    )
