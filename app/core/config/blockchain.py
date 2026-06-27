from dataclasses import dataclass

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class ChainConfig:
    rpc_url: str
    token_contract_address: str


SUPPORTED_CHAIN_IDS = {11155111, 43113, 80002}


def _get_secret_value(secret: dict, *keys: str) -> str | None:
    for key in keys:
        value = secret.get(key)
        if value:
            return str(value)
    return None


def get_chain_config(chain_id: int) -> ChainConfig:
    if chain_id not in SUPPORTED_CHAIN_IDS:
        raise ValueError(f"chain_idの設定が存在しません。 chain_id: {chain_id}")

    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets ManagerのsecretがJSON形式ではありません。")

    rpc_url = _get_secret_value(secret, f"chain_{chain_id}_rpc_url")
    token_contract_address = _get_secret_value(
        secret,
        f"chain_{chain_id}_jpyc_token_address"
    )

    if not rpc_url:
        raise ValueError(f"secretにchain_{chain_id}_rpc_urlが設定されていません。")
    if not token_contract_address:
        raise ValueError("secretにJPYCトークンアドレスが設定されていません。")

    return ChainConfig(
        rpc_url=rpc_url,
        token_contract_address=token_contract_address,
    )
