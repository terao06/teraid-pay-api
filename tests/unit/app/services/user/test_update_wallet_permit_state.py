from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    WalletNotPermittedException,
    WalletNotFoundException,
)
from app.services.user_service import UserService


class TestUpdateWalletPermitState:
    """update_wallet_permit_state の動作を検証する。"""

    @patch("app.services.user_service.Web3")
    @patch("app.services.user_service.WalletPermitRepository")
    @patch("app.services.user_service.get_payment_processor_config")
    @patch("app.services.user_service.get_wallet_permit_config")
    @patch("app.services.user_service.get_chain_config")
    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_permit_state(
        self,
        mock_repository_class,
        mock_get_chain_config,
        mock_get_wallet_permit_config,
        mock_get_payment_processor_config,
        mock_wallet_permit_repository_class,
        mock_web3_class,
    ) -> None:
        """正常系の処理結果を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        permit = {
            "value": 1000,
            "deadline": 1893456000,
            "signature_recovery_id": 27,
            "signature_first_32_bytes": "0x" + "a" * 64,
            "signature_second_32_bytes": "0x" + "b" * 64,
        }
        wallet_info = SimpleNamespace(
            wallet_id=wallet_id,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            is_permitted=False,
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = wallet_info
        mock_get_chain_config.return_value = SimpleNamespace(rpc_url="https://example.test")
        mock_get_wallet_permit_config.return_value = SimpleNamespace(
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            operator_private_key="0x" + "c" * 64,
        )
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda value: value
        mock_web3.eth.get_code.return_value = b"contract"
        mock_account = mock_web3.eth.account.from_key.return_value
        mock_account.address = "0x4444444444444444444444444444444444444444"
        mock_account.sign_transaction.return_value = SimpleNamespace(raw_transaction=b"raw")
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_web3.eth.send_raw_transaction.return_value = "0x" + "d" * 64
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        mock_contract = mock_web3.eth.contract.return_value
        mock_contract.functions.permit.return_value.build_transaction.return_value = {"tx": "permit"}
        mock_contract.functions.allowance.return_value.call.return_value = 1000

        result = UserService().update_wallet_permit_state(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
            **permit,
        )

        mock_repository.get_wallet_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_get_payment_processor_config.assert_called_once_with(chain_id=11155111)
        mock_contract.functions.permit.assert_called_once_with(
            wallet_info.wallet_address,
            "0x3333333333333333333333333333333333333333",
            permit["value"],
            permit["deadline"],
            permit["signature_recovery_id"],
            permit["signature_first_32_bytes"],
            permit["signature_second_32_bytes"],
        )
        mock_contract.functions.permit.return_value.build_transaction.assert_called_once_with({
            "from": mock_account.address,
            "nonce": 7,
            "chainId": wallet_info.chain_id,
        })
        mock_web3.eth.send_raw_transaction.assert_called_once_with(b"raw")
        mock_web3.eth.wait_for_transaction_receipt.assert_called_once_with("0x" + "d" * 64)
        assert wallet_info.is_permitted is True
        mock_repository.update_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            wallet=wallet_info,
        )
        mock_contract.functions.allowance.assert_called_once_with(
            wallet_info.wallet_address,
            "0x3333333333333333333333333333333333333333",
        )
        mock_wallet_permit_repository = mock_wallet_permit_repository_class.return_value
        mock_wallet_permit_repository.create_wallet_permit.assert_called_once()
        create_wallet_permit_kwargs = (
            mock_wallet_permit_repository.create_wallet_permit.call_args.kwargs
        )
        assert create_wallet_permit_kwargs["mysql_session"] is mysql_session
        saved_wallet_permit = create_wallet_permit_kwargs["wallet_permit"]
        assert saved_wallet_permit.wallet_id == wallet_id
        assert (
            saved_wallet_permit.token_contract_address
            == "0x2222222222222222222222222222222222222222"
        )
        assert (
            saved_wallet_permit.spender_address
            == "0x3333333333333333333333333333333333333333"
        )
        assert saved_wallet_permit.allowance_amount == "1000"
        assert saved_wallet_permit.permit_deadline == datetime(2030, 1, 1, 9, 0, 0)
        assert saved_wallet_permit.permit_tx_hash == "0x" + "d" * 64
        assert saved_wallet_permit.permitted_at is not None
        assert result is None

    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_permit_state_wallet_not_found(
        self,
        mock_repository_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = None

        with pytest.raises(WalletNotFoundException):
            UserService().update_wallet_permit_state(
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        mock_repository.get_wallet_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_repository.update_wallet.assert_not_called()

    @patch("app.services.user_service.Web3")
    @patch("app.services.user_service.get_payment_processor_config")
    @patch("app.services.user_service.get_wallet_permit_config")
    @patch("app.services.user_service.get_chain_config")
    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_permit_state_raises_when_allowance_is_insufficient(
        self,
        mock_repository_class,
        mock_get_chain_config,
        mock_get_wallet_permit_config,
        mock_get_payment_processor_config,
        mock_web3_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        wallet_info = SimpleNamespace(
            wallet_id=wallet_id,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=11155111,
            is_permitted=False,
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = wallet_info
        mock_get_chain_config.return_value = SimpleNamespace(rpc_url="https://example.test")
        mock_get_wallet_permit_config.return_value = SimpleNamespace(
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            operator_private_key="0x" + "c" * 64,
        )
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda value: value
        mock_web3.eth.get_code.return_value = b"contract"
        mock_account = mock_web3.eth.account.from_key.return_value
        mock_account.address = "0x4444444444444444444444444444444444444444"
        mock_account.sign_transaction.return_value = SimpleNamespace(raw_transaction=b"raw")
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_web3.eth.send_raw_transaction.return_value = "0x" + "d" * 64
        mock_web3.eth.wait_for_transaction_receipt.return_value = {"status": 1}
        mock_contract = mock_web3.eth.contract.return_value
        mock_contract.functions.permit.return_value.build_transaction.return_value = {"tx": "permit"}
        mock_contract.functions.allowance.return_value.call.return_value = 999

        with pytest.raises(WalletNotPermittedException):
            UserService().update_wallet_permit_state(
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        assert wallet_info.is_permitted is False
        mock_repository.update_wallet.assert_not_called()

    @patch("app.services.user_service.Web3")
    @patch("app.services.user_service.get_payment_processor_config")
    @patch("app.services.user_service.get_wallet_permit_config")
    @patch("app.services.user_service.get_chain_config")
    @patch("app.services.user_service.WalletRepository")
    def test_update_wallet_permit_state_raises_when_token_address_has_no_code(
        self,
        mock_repository_class,
        mock_get_chain_config,
        mock_get_wallet_permit_config,
        mock_get_payment_processor_config,
        mock_web3_class,
    ) -> None:
        """例外・エラー条件での動作を検証する。"""
        mysql_session = Mock()
        wallet_id = 301
        wallet_info = SimpleNamespace(
            wallet_id=wallet_id,
            wallet_address="0x1111111111111111111111111111111111111111",
            chain_id=43113,
            is_permitted=False,
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_id.return_value = wallet_info
        mock_get_chain_config.return_value = SimpleNamespace(rpc_url="https://example.test")
        mock_get_wallet_permit_config.return_value = SimpleNamespace(
            token_contract_address="0x2222222222222222222222222222222222222222",
            spender_address="0x3333333333333333333333333333333333333333",
        )
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            operator_private_key="0x" + "c" * 64,
        )
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda value: value
        mock_web3.eth.get_code.return_value = b""

        with pytest.raises(WalletNotPermittedException, match="JPYCトークンアドレス"):
            UserService().update_wallet_permit_state(
                mysql_session=mysql_session,
                wallet_id=wallet_id,
                value=1000,
                deadline=1893456000,
                signature_recovery_id=27,
                signature_first_32_bytes="0x" + "a" * 64,
                signature_second_32_bytes="0x" + "b" * 64,
            )

        mock_web3.eth.contract.assert_not_called()
        mock_repository.update_wallet.assert_not_called()
