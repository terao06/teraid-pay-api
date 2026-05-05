from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.wallet import Wallet
from app.repositories.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_wallets")
class TestGetWalletById:
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
        session: Session,
        wallet_id: int,
        expected_wallet_address: str | None,
    ) -> None:
        repository = WalletRepository()

        result = repository.get_wallet_by_id(session, wallet_id)

        if expected_wallet_address is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == wallet_id
        assert result.wallet_address == expected_wallet_address
        assert result.deleted_at is None


@pytest.mark.usefixtures("insert_wallets")
class TestGetWalletByAddress:
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
        session: Session,
        wallet_address: str,
        expected_wallet_id: int | None,
    ) -> None:
        repository = WalletRepository()

        result = repository.get_wallet_by_address(session, wallet_address)

        if expected_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet_id
        assert result.wallet_address == wallet_address
        assert result.deleted_at is None


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestCreateWallet:
    def test_create_wallet(
        self,
        session: Session,
    ) -> None:
        repository = WalletRepository()
        wallet = Wallet(
            wallet_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        saved_wallet = repository.create_wallet(session, wallet)
        session.flush()

        assert saved_wallet.wallet_id is not None
        assert saved_wallet.wallet_address == "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        assert saved_wallet.chain_type == "ethereum"
        assert saved_wallet.network_name == "sepolia"
        assert saved_wallet.token_symbol == "JPYC"
        assert saved_wallet.chain_id == 11155111
        assert saved_wallet.is_active is True
        assert saved_wallet.is_approval is True
        assert saved_wallet.verified_at == datetime(2026, 4, 13, 12, 0, 0)


@pytest.mark.usefixtures("insert_wallets")
class TestUpdateWallet:
    def test_update_wallet(
        self,
        session: Session,
    ) -> None:
        repository = WalletRepository()
        wallet = session.query(Wallet).where(Wallet.wallet_id == 301).one()
        before_updated_at = wallet.updated_at
        verified_at = datetime(2026, 4, 13, 12, 0, 0)

        wallet.wallet_name = "updated wallet"
        wallet.is_active = False
        wallet.verified_at = verified_at

        updated_wallet = repository.update_wallet(session, wallet)
        session.flush()
        session.expire_all()

        after = session.query(Wallet).where(Wallet.wallet_id == 301).one()
        assert updated_wallet.wallet_id == 301
        assert after.wallet_name == "updated wallet"
        assert after.is_active is False
        assert after.verified_at == verified_at
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestDeleteWallet:
    def test_delete_wallet_by_wallet_id(
        self,
        session: Session,
    ) -> None:
        repository = WalletRepository()
        wallet_id = 301

        before = session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_wallet_by_wallet_id(session, wallet_id)
        session.flush()
        session.expire_all()

        after = session.query(Wallet).where(Wallet.wallet_id == wallet_id).one()
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at
