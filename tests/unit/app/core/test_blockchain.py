from unittest.mock import patch

import pytest

from app.core.config.blockchain import get_chain_config


def test_get_chain_config_returns_sepolia_config_from_secret():
    with patch("app.core.config.blockchain.SecretManager") as secret_manager_class:
        secret_manager_class.return_value.get_secret.return_value = {
            "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/test-api-key",
            "chain_11155111_jpyc_token_address": "0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29",
        }

        chain_config = get_chain_config(11155111)

    assert chain_config.rpc_url == "https://sepolia.infura.io/v3/test-api-key"
    assert chain_config.token_contract_address == "0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29"
    secret_manager_class.return_value.get_secret.assert_called_once_with("secret")


def test_get_chain_config_returns_avalanche_fuji_config_from_secret():
    with patch("app.core.config.blockchain.SecretManager") as secret_manager_class:
        secret_manager_class.return_value.get_secret.return_value = {
            "chain_43113_rpc_url": "https://api.avax-test.network/ext/bc/C/rpc",
            "chain_43113_jpyc_token_address": "0xe8aE6fa0212e575d8C80387D337dea0e6083d75b",
        }

        chain_config = get_chain_config(43113)

    assert chain_config.rpc_url == "https://api.avax-test.network/ext/bc/C/rpc"
    assert chain_config.token_contract_address == "0xe8aE6fa0212e575d8C80387D337dea0e6083d75b"
    secret_manager_class.return_value.get_secret.assert_called_once_with("secret")


def test_get_chain_config_returns_polygon_amoy_config_from_secret():
    with patch("app.core.config.blockchain.SecretManager") as secret_manager_class:
        secret_manager_class.return_value.get_secret.return_value = {
            "chain_80002_rpc_url": "https://rpc-amoy.polygon.technology",
            "chain_80002_jpyc_token_address": "0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29",
        }

        chain_config = get_chain_config(80002)

    assert chain_config.rpc_url == "https://rpc-amoy.polygon.technology"
    assert chain_config.token_contract_address == "0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29"
    secret_manager_class.return_value.get_secret.assert_called_once_with("secret")


def test_get_chain_config_raises_when_rpc_url_is_missing():
    with patch("app.core.config.blockchain.SecretManager") as secret_manager_class:
        secret_manager_class.return_value.get_secret.return_value = {
            "chain_11155111_jpyc_token_address": "0xE7C3D8C9a439feDe00D2600032D5dB0Be71C3c29",
        }

        with pytest.raises(ValueError, match="chain_11155111_rpc_url"):
            get_chain_config(11155111)


def test_get_chain_config_raises_when_token_contract_address_is_missing():
    with patch("app.core.config.blockchain.SecretManager") as secret_manager_class:
        secret_manager_class.return_value.get_secret.return_value = {
            "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/test-api-key",
        }

        with pytest.raises(ValueError, match="JPYCトークンアドレス"):
            get_chain_config(11155111)


def test_get_chain_config_raises_when_chain_id_is_not_supported():
    with pytest.raises(ValueError, match="chain_idの設定が存在しません"):
        get_chain_config(1)
