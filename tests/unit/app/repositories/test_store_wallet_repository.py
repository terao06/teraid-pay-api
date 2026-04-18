from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_wallet_nonce import StoreWalletNonce
from app.repositories.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
class TestGetStoreWalletList:
    @pytest.mark.parametrize(
        ("store_id", "expected_wallets"),
        [
            (
                None,
                [
                    {
                        "store_wallet_id": 201,
                        "store_id": 101,
                        "wallet_address": "0x1111111111111111111111111111111111111111",
                        "chain_type": "ETH",
                        "network_name": "mainnet",
                        "is_active": True,
                        "verified_at": "2024-01-10 12:00:00",
                    },
                    {
                        "store_wallet_id": 202,
                        "store_id": 101,
                        "wallet_address": "0x2222222222222222222222222222222222222222",
                        "chain_type": "POLYGON",
                        "network_name": "amoy",
                        "is_active": False,
                        "verified_at": None,
                    },
                    {
                        "store_wallet_id": 204,
                        "store_id": 102,
                        "wallet_address": "0x4444444444444444444444444444444444444444",
                        "chain_type": "ETH",
                        "network_name": "mainnet",
                        "is_active": True,
                        "verified_at": "2024-04-01 00:00:00",
                    },
                ],
            ),
            (
                101,
                [
                    {
                        "store_wallet_id": 201,
                        "store_id": 101,
                        "wallet_address": "0x1111111111111111111111111111111111111111",
                        "chain_type": "ETH",
                        "network_name": "mainnet",
                        "is_active": True,
                        "verified_at": "2024-01-10 12:00:00",
                    },
                    {
                        "store_wallet_id": 202,
                        "store_id": 101,
                        "wallet_address": "0x2222222222222222222222222222222222222222",
                        "chain_type": "POLYGON",
                        "network_name": "amoy",
                        "is_active": False,
                        "verified_at": None,
                    },
                ],
            ),
            (103, []),
        ],
    )
    def test_get_store_wallet_list(
        self,
        session: Session,
        store_id: int | None,
        expected_wallets: list[dict],
    ) -> None:
        """条件に応じた店舗ウォレット一覧を取得できることを確認する。"""
        repository = StoreRepository()

        result = sorted(
            repository.get_store_wallet_list(session, store_id),
            key=lambda wallet: wallet.store_wallet_id,
        )

        assert len(result) == len(expected_wallets)
        for wallet, expected in zip(result, expected_wallets):
            assert wallet.store_wallet_id == expected["store_wallet_id"]
            assert wallet.store_id == expected["store_id"]
            assert wallet.wallet_address == expected["wallet_address"]
            assert wallet.chain_type == expected["chain_type"]
            assert wallet.network_name == expected["network_name"]
            assert wallet.is_active == expected["is_active"]
            verified_at = wallet.verified_at.isoformat(sep=" ") if wallet.verified_at else None
            assert verified_at == expected["verified_at"]


@pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
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
        """店舗 ID に対応する店舗を取得できることを確認する。"""
        repository = StoreRepository()

        result = repository.get_store_by_id(session, store_id)

        if expected_store_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_id == expected_store_id


@pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
class TestGetStoreWalletByAddress:
    @pytest.mark.parametrize(
        ("wallet_address", "chain_type", "network_name", "expected_store_wallet_id"),
        [
            (
                "0x1111111111111111111111111111111111111111",
                "ETH",
                "mainnet",
                201,
            ),
            (
                "0x3333333333333333333333333333333333333333",
                "ETH",
                "sepolia",
                None,
            ),
            (
                "0x5555555555555555555555555555555555555555",
                "ETH",
                "mainnet",
                205,
            ),
            (
                "0x9999999999999999999999999999999999999999",
                "ETH",
                "mainnet",
                None,
            ),
        ],
    )
    def test_get_store_wallet_by_address(
        self,
        session: Session,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        expected_store_wallet_id: int | None,
    ) -> None:
        """アドレスとチェーン条件に一致するウォレットを取得できることを確認する。"""
        repository = StoreRepository()

        result = repository.get_store_wallet_by_address(
            session=session,
            wallet_address=wallet_address,
            chain_type=chain_type,
            network_name=network_name,
        )

        if expected_store_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_wallet_id == expected_store_wallet_id
        assert result.wallet_address == wallet_address
        assert result.chain_type == chain_type
        assert result.network_name == network_name


class TestCreateStoreWalletNonce:
    def test_create_store_wallet_nonce(
        self,
        session: Session,
    ) -> None:
        """nonce を新規保存できることを確認する。"""
        repository = StoreRepository()
        nonce = StoreWalletNonce(
            store_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        repository.create_store_wallet_nonce(session, nonce)
        session.flush()

        saved_nonce = session.query(StoreWalletNonce).one()

        assert saved_nonce.store_wallet_nonce_id is not None
        assert saved_nonce.store_id == 101
        assert saved_nonce.wallet_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert saved_nonce.chain_type == "ethereum"
        assert saved_nonce.network_name == "sepolia"
        assert saved_nonce.nonce == "test-store-wallet-nonce"
        assert saved_nonce.expires_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_nonce.used_at is None


@pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
class TestCreateStoreWallet:
    def test_create_store_wallet(
        self,
        session: Session,
    ) -> None:
        """ウォレットを新規保存できることを確認する。"""
        repository = StoreRepository()
        wallet = StoreWallet(
            store_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            is_primary=True,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        repository.create_store_wallet(session, wallet)
        session.flush()

        saved_wallet = (
            session.query(StoreWallet)
            .filter(StoreWallet.wallet_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            .one()
        )

        assert saved_wallet.store_wallet_id is not None
        assert saved_wallet.store_id == 101
        assert saved_wallet.wallet_address == "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        assert saved_wallet.chain_type == "ethereum"
        assert saved_wallet.network_name == "sepolia"
        assert saved_wallet.is_primary is True
        assert saved_wallet.is_active is True
        assert saved_wallet.verified_at == datetime(2026, 4, 13, 12, 0, 0)
        assert saved_wallet.created_at is not None
        assert saved_wallet.updated_at is not None
        assert saved_wallet.deleted_at is None


@pytest.mark.usefixtures("insert_stores", "insert_store_wallets")
class TestUnsetPrimaryWallets:
    def test_unset_primary_wallets(
        self,
        session: Session,
    ) -> None:
        """対象店舗の有効な主ウォレットだけ primary を解除することを確認する。"""
        repository = StoreRepository()

        repository.unset_primary_wallets(session, 101)
        session.flush()

        wallets = {
            wallet.store_wallet_id: wallet
            for wallet in session.query(StoreWallet).order_by(StoreWallet.store_wallet_id).all()
        }

        assert wallets[201].is_primary is False
        assert wallets[201].updated_at is not None
        assert wallets[201].updated_at > datetime(2024, 1, 11, 10, 30, 0)

        assert wallets[202].is_primary is False
        assert wallets[203].is_primary is False
        assert wallets[204].is_primary is True
        assert wallets[205].is_primary is True

    def test_unset_primary_wallets_noop_when_no_primary_wallets(
        self,
        session: Session,
    ) -> None:
        """解除対象がない場合は既存状態を維持することを確認する。"""
        repository = StoreRepository()

        before_wallet_202 = session.query(StoreWallet).filter(StoreWallet.store_wallet_id == 202).one()
        before_updated_at = before_wallet_202.updated_at

        repository.unset_primary_wallets(session, 101)
        session.flush()
        repository.unset_primary_wallets(session, 101)
        session.flush()

        after_wallet_202 = session.query(StoreWallet).filter(StoreWallet.store_wallet_id == 202).one()
        after_wallet_201 = session.query(StoreWallet).filter(StoreWallet.store_wallet_id == 201).one()

        assert after_wallet_202.is_primary is False
        assert after_wallet_202.updated_at == before_updated_at
        assert after_wallet_201.is_primary is False


@pytest.mark.usefixtures("insert_stores", "insert_store_wallet_nonces")
class TestGetLatestAvailableNonce:
    def test_get_latest_available_nonce(
        self,
        session: Session,
    ) -> None:
        """利用可能な最新 nonce を取得できることを確認する。"""
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
        """条件に一致する nonce がない場合は None を返すことを確認する。"""
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


@pytest.mark.usefixtures("insert_stores", "insert_store_wallet_nonces")
class TestUpdateStoreWalletNonce:
    def test_update_store_wallet_nonce(
        self,
        session: Session,
    ) -> None:
        """nonce の更新内容を保存できることを確認する。"""
        repository = StoreRepository()
        nonce = (
            session.query(StoreWalletNonce)
            .filter(StoreWalletNonce.store_wallet_nonce_id == 2)
            .one()
        )
        used_at = datetime(2026, 4, 13, 11, 30, 0)

        nonce.used_at = used_at
        repository.update_store_wallet_nonce(session, nonce)
        session.flush()
        session.expire_all()

        saved_nonce = (
            session.query(StoreWalletNonce)
            .filter(StoreWalletNonce.store_wallet_nonce_id == 2)
            .one()
        )

        assert saved_nonce.store_wallet_nonce_id == 2
        assert saved_nonce.nonce == "available-latest"
        assert saved_nonce.used_at == used_at
