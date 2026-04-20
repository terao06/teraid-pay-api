from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet
from app.repositories.nonce_repository import NonceRepository
from app.repositories.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetStoreWallet:
    @pytest.mark.parametrize(
        ("store_id", "expected_wallet"),
        [
            (
                None,
                {
                    "store_wallet_id": 201,
                    "store_id": 101,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "mainnet",
                    "is_active": True,
                    "verified_at": "2024-01-10 12:00:00",
                },
            ),
            (
                101,
                {
                    "store_wallet_id": 201,
                    "store_id": 101,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "mainnet",
                    "is_active": True,
                    "verified_at": "2024-01-10 12:00:00",
                },
            ),
        ],
    )
    def test_get_store_wallet(
        self,
        session: Session,
        store_id: int | None,
        expected_wallet: dict,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_store_wallet(session, store_id)

        assert result is not None
        assert result.store_wallet_id == expected_wallet["store_wallet_id"]
        assert result.store_id == expected_wallet["store_id"]
        assert result.wallet_address == expected_wallet["wallet_address"]
        assert result.chain_type == expected_wallet["chain_type"]
        assert result.network_name == expected_wallet["network_name"]
        assert result.is_active == expected_wallet["is_active"]
        verified_at = result.verified_at.isoformat(sep=" ") if result.verified_at else None
        assert verified_at == expected_wallet["verified_at"]


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetStoreById:
    @pytest.mark.parametrize(
        ("store_id", "expected_store_id"),
        [
            (101, 101),
            (102, 102),
            (103, None),
            (999, None),
        ],
    )
    def test_get_store_by_id(
        self,
        session: Session,
        store_id: int,
        expected_store_id: int | None,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_store_by_id(session, store_id)

        if expected_store_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_id == expected_store_id


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetWalletByStoreId:
    @pytest.mark.parametrize(
        ("store_id", "chain_type", "network_name", "expected_wallet_id"),
        [
            (101, "ETH", "mainnet", 301),
            (101, "ETH", "sepolia", None),
            (102, "ETH", "mainnet", 304),
            (999, "ETH", "mainnet", None),
        ],
    )
    def test_get_wallet_by_store_id(
        self,
        session: Session,
        store_id: int,
        chain_type: str,
        network_name: str,
        expected_wallet_id: int | None,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_wallet_by_store_id(
            session=session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
        )

        if expected_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet_id
        assert result.chain_type == chain_type
        assert result.network_name == network_name


@pytest.mark.usefixtures("insert_stores")
class TestCreateStoreNonce:
    def test_create_store_nonce(
        self,
        session: Session,
    ) -> None:
        repository = StoreRepository()
        nonce = Nonce(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        saved_nonce = NonceRepository().create_nonce(session, nonce)

        store_nonce = StoreNonce(store_id=101, nonce_id=saved_nonce.nonce_id)
        repository.create_store_nonce(session, store_nonce)
        session.flush()

        saved_store_nonce = (
            session.query(StoreNonce)
            .filter(StoreNonce.store_id == 101, StoreNonce.nonce_id == saved_nonce.nonce_id)
            .one()
        )

        assert saved_store_nonce.store_nonce_id is not None
        assert saved_store_nonce.store_id == 101
        assert saved_store_nonce.nonce_id == saved_nonce.nonce_id
        assert saved_store_nonce.created_at is not None
        assert saved_store_nonce.updated_at is not None
        assert saved_store_nonce.deleted_at is None


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestCreateStoreWallet:
    def test_create_store_wallet(
        self,
        session: Session,
    ) -> None:
        repository = StoreRepository()
        new_wallet = Wallet(
            wallet_address="0xcccccccccccccccccccccccccccccccccccccccc",
            chain_type="ethereum",
            network_name="sepolia",
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        session.add(new_wallet)
        session.flush()

        store_wallet = StoreWallet(
            store_id=101,
            wallet_id=new_wallet.wallet_id,
        )

        repository.create_store_wallet(session, store_wallet)
        session.flush()

        saved_store_wallet = (
            session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == new_wallet.wallet_id)
            .one()
        )

        assert saved_store_wallet.store_wallet_id is not None
        assert saved_store_wallet.store_id == 101
        assert saved_store_wallet.wallet_id == new_wallet.wallet_id
        assert saved_store_wallet.created_at is not None
        assert saved_store_wallet.updated_at is not None
        assert saved_store_wallet.deleted_at is None


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestGetLatestAvailableNonce:
    def test_get_latest_available_nonce(
        self,
        session: Session,
    ) -> None:
        repository = StoreRepository()
        base_expires_at = datetime(2026, 4, 13, 12, 0, 0)

        result = repository.get_latest_available_nonce(
            session=session,
            store_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=base_expires_at,
        )

        assert result is not None
        assert result.nonce == "available-latest"
        assert result.used_at is None
        assert result.expires_at == datetime(2026, 4, 13, 12, 5, 0)

    def test_get_latest_available_nonce_returns_none(
        self,
        session: Session,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_latest_available_nonce(
            session=session,
            store_id=102,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is None


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestDeleteStoreNonceByNonceId:
    def test_delete_store_nonce_by_nonce_id(
        self,
        session: Session,
    ) -> None:
        """存在する nonce_id を指定した場合、対象 StoreNonce の deleted_at が設定されること。"""
        repository = StoreRepository()
        target_nonce_id = 1

        before = (
            session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert before.deleted_at is None

        repository.delete_store_nonce_by_nonce_id(session, target_nonce_id)
        session.flush()
        session.expire_all()

        after = (
            session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert after.deleted_at is not None

    def test_delete_store_nonce_by_nonce_id_not_found(
        self,
        session: Session,
    ) -> None:
        """存在しない nonce_id を指定した場合、いずれの StoreNonce も更新されないこと。"""
        repository = StoreRepository()
        non_existent_nonce_id = 99999

        repository.delete_store_nonce_by_nonce_id(session, non_existent_nonce_id)
        session.flush()
        session.expire_all()

        updated = (
            session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .all()
        )
        assert len(updated) == 0
