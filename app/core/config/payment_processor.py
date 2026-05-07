from dataclasses import dataclass

from app.core.aws.secret_manager import SecretManager


@dataclass(frozen=True)
class PaymentProcessorConfig:
    token_contract_address: str
    payment_processor_address: str
    operator_private_key: str


def _get_secret_value(secret: dict, *keys: str) -> str | None:
    for key in keys:
        value = secret.get(key)
        if value:
            return str(value)
    return None


def get_payment_processor_config(chain_id: int) -> PaymentProcessorConfig:
    secret = SecretManager().get_secret("secret")
    if not isinstance(secret, dict):
        raise ValueError("Secrets ManagerのsecretがJSON形式ではありません。")

    token_contract_address = _get_secret_value(
        secret,
        f"chain_{chain_id}_jpyc_token_address",
        "jpyc_token_address",
        "JPYC_TOKEN_ADDRESS",
    )
    payment_processor_address = _get_secret_value(
        secret,
        f"chain_{chain_id}_payment_processor_address",
        "payment_processor_address",
        "PAYMENT_PROCESSOR_ADDRESS",
    )
    operator_private_key = _get_secret_value(
        secret,
        f"chain_{chain_id}_payment_operator_private_key",
        "payment_operator_private_key",
        "PAYMENT_OPERATOR_PRIVATE_KEY",
    )

    if not token_contract_address:
        raise ValueError("secretにJPYCトークンアドレスが設定されていません。")
    if not payment_processor_address:
        raise ValueError("secretにPaymentProcessorアドレスが設定されていません。")
    if not operator_private_key:
        raise ValueError("secretにPayment operator private keyが設定されていません。")

    return PaymentProcessorConfig(
        token_contract_address=token_contract_address,
        payment_processor_address=payment_processor_address,
        operator_private_key=operator_private_key,
    )
