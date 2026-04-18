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
    def build_sign_message(
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        nonce: str,
    ) -> str:
        """署名検証用のメッセージを組み立てる。

        Args:
            store_id: 対象店舗の ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            nonce: 署名用 nonce。

        Returns:
            署名対象のメッセージ文字列。
        """
        return (
            "Store wallet registration\n\n"
            f"store_id: {store_id}\n"
            f"wallet_address: {wallet_address}\n"
            f"chain_type: {chain_type}\n"
            f"network_name: {network_name}\n"
            f"nonce: {nonce}\n\n"
            "この署名は店舗ウォレット登録確認のためのものであり、"
            "ガス代はかかりません。"
        )
