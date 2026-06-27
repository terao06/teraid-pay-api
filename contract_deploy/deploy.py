from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from solcx import compile_standard, install_solc, set_solc_version
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "contracts" / "PaymentProcessor.sol"
BUILD_DIR = ROOT / "build"
SOLC_VERSION = "0.8.28"


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def checksum(web3: Web3, address: str, name: str) -> str:
    if not web3.is_address(address):
        raise RuntimeError(f"{name} is not a valid address: {address}")
    return web3.to_checksum_address(address)


ERC20_PERMIT_CHECK_ABI = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "nonces",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def validate_token_contract(web3: Web3, token: str, owner: str) -> None:
    if not web3.eth.get_code(token):
        raise RuntimeError(
            "JPYC_TOKEN_ADDRESS must be a token contract address on the target chain, "
            f"but no contract code was found at {token}"
        )

    token_contract = web3.eth.contract(address=token, abi=ERC20_PERMIT_CHECK_ABI)
    try:
        token_name = token_contract.functions.name().call()
        token_symbol = token_contract.functions.symbol().call()
        token_contract.functions.nonces(owner).call()
    except Exception as exc:
        raise RuntimeError(
            "JPYC_TOKEN_ADDRESS must be an ERC20Permit-compatible token contract. "
            f"Failed to call name(), symbol(), or nonces(address) at {token}"
        ) from exc

    print(f"validated_token name={token_name} symbol={token_symbol} address={token}")


def compile_contract() -> tuple[list[dict[str, Any]], str]:
    source = CONTRACT_PATH.read_text(encoding="utf-8")

    install_solc(SOLC_VERSION)
    set_solc_version(SOLC_VERSION)

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                CONTRACT_PATH.name: {
                    "content": source,
                },
            },
            "settings": {
                "optimizer": {
                    "enabled": True,
                    "runs": 200,
                },
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode.object"],
                    },
                },
            },
        },
        solc_version=SOLC_VERSION,
    )

    contract = compiled["contracts"][CONTRACT_PATH.name]["PaymentProcessor"]
    abi = contract["abi"]
    bytecode = contract["evm"]["bytecode"]["object"]

    BUILD_DIR.mkdir(exist_ok=True)
    (BUILD_DIR / "PaymentProcessor.abi.json").write_text(
        json.dumps(abi, indent=2),
        encoding="utf-8",
    )
    (BUILD_DIR / "PaymentProcessor.bytecode.txt").write_text(
        bytecode,
        encoding="utf-8",
    )

    return abi, bytecode


def main() -> None:
    env_file = os.getenv("ENV_FILE", ".env.polygon")
    load_env(ROOT / env_file)

    rpc_url = required_env("RPC_URL")
    private_key = required_env("DEPLOYER_PRIVATE_KEY")
    token_address = required_env("JPYC_TOKEN_ADDRESS")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not web3.is_connected():
        raise RuntimeError(f"failed to connect RPC_URL: {rpc_url}")

    account = web3.eth.account.from_key(private_key)
    deployer = account.address
    owner = os.getenv("CONTRACT_OWNER_ADDRESS", deployer)
    operator = os.getenv("PAYMENT_OPERATOR_ADDRESS", deployer)

    owner = checksum(web3, owner, "CONTRACT_OWNER_ADDRESS")
    operator = checksum(web3, operator, "PAYMENT_OPERATOR_ADDRESS")
    token = checksum(web3, token_address, "JPYC_TOKEN_ADDRESS")
    validate_token_contract(web3, token, owner)

    abi, bytecode = compile_contract()
    contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = web3.eth.get_transaction_count(deployer)
    chain_id = web3.eth.chain_id
    tx = contract.constructor(owner, operator, token).build_transaction(
        {
            "from": deployer,
            "nonce": nonce,
            "chainId": chain_id,
        }
    )

    gas_multiplier = float(os.getenv("GAS_MULTIPLIER", "1.2"))
    estimated_gas = web3.eth.estimate_gas(tx)
    tx["gas"] = int(estimated_gas * gas_multiplier)

    latest_block = web3.eth.get_block("latest")
    if "baseFeePerGas" in latest_block:
        priority_fee = web3.to_wei(float(os.getenv("MAX_PRIORITY_FEE_GWEI", "2")), "gwei")
        tx["maxPriorityFeePerGas"] = priority_fee
        tx["maxFeePerGas"] = int(latest_block["baseFeePerGas"] * 2 + priority_fee)
    else:
        tx["gasPrice"] = web3.eth.gas_price

    signed_tx = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status != 1:
        raise RuntimeError(f"deployment failed: tx={tx_hash.hex()}")

    result = {
        "network_chain_id": chain_id,
        "deployer": deployer,
        "owner": owner,
        "operator": operator,
        "token": token,
        "payment_processor": receipt.contractAddress,
        "transaction_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
    }

    output_path = BUILD_DIR / "deployment.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    print(f"saved={output_path}")


if __name__ == "__main__":
    main()
