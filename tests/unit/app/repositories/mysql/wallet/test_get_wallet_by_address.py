import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_wallets")
class TestGetWalletByAddress:
    """get_wallet_by_address の動作を検証する。"""

    @pytest.mark.parametrize(
        ("wallet_address", "expected_wallet_id"),
        [
            ("0x1111111111111111111111111111111111111111", 301),
            ("0x3333333333333333333333333333333333333333", None),
            ("0xffffffffffffffffffffffffffffffffffffffff", None),
        ],
    )
    def test_get_wallet_by_address(
        self,
        mysql_session: Session,
        wallet_address: str,
        expected_wallet_id: int | None,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = WalletRepository()

        result = repository.get_wallet_by_address(mysql_session, wallet_address)

        if expected_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet_id
        assert result.wallet_address == wallet_address
        assert result.deleted_at is None
