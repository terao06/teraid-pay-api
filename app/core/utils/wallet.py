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
