from dataclasses import dataclass

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class ChainConfig:
    rpc_url: str
    token_contract_address: str


# テスト用ブロックへのチェーン関連で使用するurlはapi key必要
INFURA_RPC_URL_TEMPLATES = {
    11155111: "https://sepolia.infura.io/v3/{api_key}",
}


CHAIN_CONFIG = {
    11155111: ChainConfig(
        rpc_url=INFURA_RPC_URL_TEMPLATES[11155111],
        token_contract_address="0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29",
    ),
    43113: ChainConfig(
        rpc_url="https://api.avax-test.network/ext/bc/C/rpc",
        token_contract_address="0xe8aE6fa0212e575d8C80387D337dea0e6083d75b",
    ),
    80002: ChainConfig(
        rpc_url="https://rpc-amoy.polygon.technology",
        token_contract_address="0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29",
    ),
}


def _get_infura_api_key() -> str:
    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets ManagerのsecretがJSON形式ではありません。")

    api_key = secret.get("sepolia_infra_api_key")
    if not api_key:
        raise ValueError("secretにsepolia_infra_api_keyが設定されていません。")

    return str(api_key)


def get_chain_config(chain_id: int) -> ChainConfig:
    if chain_id not in CHAIN_CONFIG:
        raise ValueError(f"chain_idの設定が存在しません。 chain_id: {chain_id}")

    chain_config = CHAIN_CONFIG[chain_id]
    if chain_id in INFURA_RPC_URL_TEMPLATES:
        return ChainConfig(
            rpc_url=chain_config.rpc_url.format(api_key=_get_infura_api_key()),
            token_contract_address=chain_config.token_contract_address,
        )

    return chain_config
