from eth_account import Account
from eth_account.messages import encode_defunct

from app.core.exceptions.custom_exception import UnauthorizedException


class WalletUtil:
    @staticmethod
    def normalize_wallet_address(wallet_address: str) -> str:
        """ウォレットアドレスを正規化する。

        Args:
            wallet_address: 正規化対象のウォレットアドレス。

        Returns:
            小文字化したウォレットアドレス。
        """
        if not wallet_address:
            raise ValueError("ウォレットアドレスが空です。")

        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError("ウォレットアドレス形式が不正です。")

        return wallet_address.lower()
    
    @staticmethod
    def recover_address(
        message: str,
        signature: str,
    ) -> str:
        """署名からウォレットアドレスを復元する。

        Args:
            message: 署名対象メッセージ。
            signature: 署名値。

        Returns:
            復元したウォレットアドレス。
        """
        try:
            encoded_message = encode_defunct(text=message)
            return Account.recover_message(
                encoded_message,
                signature=signature,
            )
        except Exception:
            raise UnauthorizedException("認証に失敗しました。")
