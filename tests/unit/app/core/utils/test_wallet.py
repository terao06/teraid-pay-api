from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import UnauthorizedException
from app.core.utils.wallet import WalletUtil


class TestRecoverAddress:
    @patch("app.core.utils.wallet.Account.recover_message")
    @patch("app.core.utils.wallet.encode_defunct")
    def test_recover_address_returns_recovered_wallet_address(
        self,
        mock_encode_defunct,
        mock_recover_message,
    ) -> None:
        message = "sign this message"
        signature = "0xsigned"
        encoded_message = Mock()
        recovered_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"

        mock_encode_defunct.return_value = encoded_message
        mock_recover_message.return_value = recovered_address

        result = WalletUtil.recover_address(
            message=message,
            signature=signature,
        )

        mock_encode_defunct.assert_called_once_with(text=message)
        mock_recover_message.assert_called_once_with(
            encoded_message,
            signature=signature,
        )
        assert result == recovered_address

    @patch("app.core.utils.wallet.Account.recover_message")
    @patch("app.core.utils.wallet.encode_defunct")
    def test_recover_address_raises_unauthorized_when_recover_fails(
        self,
        mock_encode_defunct,
        mock_recover_message,
    ) -> None:
        message = "sign this message"
        signature = "0xinvalid"
        encoded_message = Mock()

        mock_encode_defunct.return_value = encoded_message
        mock_recover_message.side_effect = Exception("recover failed")

        with pytest.raises(UnauthorizedException):
            WalletUtil.recover_address(
                message=message,
                signature=signature,
            )

        mock_encode_defunct.assert_called_once_with(text=message)
        mock_recover_message.assert_called_once_with(
            encoded_message,
            signature=signature,
        )
