from dataclasses import dataclass

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class WalletPermitConfig:
    token_contract_address: str
    spender_address: str


def _get_secret_value(secret: dict, *keys: str) -> str | None:
    for key in keys:
        value = secret.get(key)
        if value:
            return str(value)
    return None


def get_wallet_permit_config(chain_id: int) -> WalletPermitConfig:
    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets ManagerのsecretがJSON形式ではありません。")

    token_contract_address = _get_secret_value(
        secret,
        f"chain_{chain_id}_jpyc_token_address",
        "jpyc_token_address",
        "JPYC_TOKEN_ADDRESS",
    )
    spender_address = _get_secret_value(
        secret,
        f"chain_{chain_id}_payment_processor_address",
        "payment_processor_address",
        "PAYMENT_PROCESSOR_ADDRESS",
    )

    if not token_contract_address:
        raise ValueError("secretにJPYCトークンアドレスが設定されていません。")
    if not spender_address:
        raise ValueError("secretにPaymentProcessorアドレスが設定されていません。")

    return WalletPermitConfig(
        token_contract_address=token_contract_address,
        spender_address=spender_address,
    )
