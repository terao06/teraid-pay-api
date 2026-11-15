import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_wallets")
class TestGetWalletById:
    """get_wallet_by_id の動作を検証する。"""

    @pytest.mark.parametrize(
        ("wallet_id", "expected_wallet_address"),
        [
            (301, "0x1111111111111111111111111111111111111111"),
            (303, None),
            (999, None),
        ],
    )
    def test_get_wallet_by_id(
        self,
        mysql_session: Session,
        wallet_id: int,
        expected_wallet_address: str | None,
    ) -> None:
        """正常系の処理結果を検証する。"""
        repository = WalletRepository()

        result = repository.get_wallet_by_id(mysql_session, wallet_id)

        if expected_wallet_address is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == wallet_id
        assert result.wallet_address == expected_wallet_address
        assert result.deleted_at is None
