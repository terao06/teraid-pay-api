from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.user_wallet import UserWallet
from app.models.mysql.user_nonce import UserNonce
from app.repositories.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestGetUserWallet:
    """get_user_wallet の unit test。"""

    @pytest.mark.parametrize(
        ("user_id", "expected_wallet"),
        [
            (
                101,
                {
                    "wallet_id": 301,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "mainnet",
                    "is_active": True,
                    "verified_at": "2024-01-10 12:00:00",
                },
            ),
            (
                999,
                None,
            ),
            (
                103,
                None,
            ),
        ],
    )
    def test_get_user_wallet(
        self,
        session: Session,
        user_id: int,
        expected_wallet: dict | None,
    ) -> None:
        """ユーザーに紐づくウォレットを取得し、未存在時は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_user_wallet(session, user_id)

        if expected_wallet is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet["wallet_id"]
        assert result.wallet_address == expected_wallet["wallet_address"]
        assert result.chain_type == expected_wallet["chain_type"]
        assert result.network_name == expected_wallet["network_name"]
        assert result.is_active == expected_wallet["is_active"]
        verified_at = result.verified_at.isoformat(sep=" ") if result.verified_at else None
        assert verified_at == expected_wallet["verified_at"]


@pytest.mark.usefixtures("insert_users")
class TestGetUserById:
    """get_user_by_id の unit test。"""

    @pytest.mark.parametrize(
        ("user_id", "expected_user_id"),
        [
            (101, 101),
            (102, 102),
            (103, None),
            (999, None),
        ],
    )
    def test_get_user_by_id(
        self,
        session: Session,
        user_id: int,
        expected_user_id: int | None,
    ) -> None:
        """ユーザー ID からユーザー情報を取得し、論理削除と未存在は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_user_by_id(session, user_id)

        if expected_user_id is None:
            assert result is None
            return

        assert result is not None
        assert result.user_id == expected_user_id


@pytest.mark.usefixtures("insert_users", "insert_nonces")
class TestCreateUserNonce:
    """create_user_nonce の unit test。"""

    def test_create_user_nonce(
        self,
        session: Session,
    ) -> None:
        """user_nonce を追加し、flush 後に永続化内容を取得できることを検証する。"""
        repository = UserRepository()
        user_nonce = UserNonce(
            user_id=101,
            nonce_id=1,
        )

        repository.create_user_nonce(session, user_nonce)
        session.flush()
        session.expire_all()

        saved_user_nonce = (
            session.query(UserNonce)
            .filter(UserNonce.user_nonce_id == user_nonce.user_nonce_id)
            .one()
        )

        assert saved_user_nonce.user_nonce_id is not None
        assert saved_user_nonce.user_id == 101
        assert saved_user_nonce.nonce_id == 1
        assert saved_user_nonce.created_at is not None
        assert saved_user_nonce.updated_at is not None
        assert saved_user_nonce.deleted_at is None


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestGetWalletByUserId:
    """get_wallet_by_user_id の unit test。"""

    @pytest.mark.parametrize(
        ("user_id", "chain_type", "network_name", "expected_wallet_id"),
        [
            (101, "ETH", "mainnet", 301),
            (101, "ETH", "goerli", None),
            (101, "ETH", "sepolia", None),
            (102, "ETH", "mainnet", 304),
            (999, "ETH", "mainnet", None),
        ],
    )
    def test_get_wallet_by_user_id(
        self,
        session: Session,
        user_id: int,
        chain_type: str,
        network_name: str,
        expected_wallet_id: int | None,
    ) -> None:
        """ユーザーに紐づく chain/network 指定の wallet を取得し、未存在時は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_wallet_by_user_id(
            session=session,
            user_id=user_id,
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


@pytest.mark.usefixtures("insert_users", "insert_nonces", "insert_user_nonces")
class TestGetLatestAvailableNonce:
    """get_latest_available_nonce の unit test。"""

    def test_get_latest_available_nonce(
        self,
        session: Session,
    ) -> None:
        """条件に一致する未使用かつ有効期限内の最新 nonce を返すことを検証する。"""
        repository = UserRepository()

        result = repository.get_latest_available_nonce(
            session=session,
            user_id=101,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is not None
        assert result.nonce_id == 2
        assert result.nonce == "available-latest"
        assert result.used_at is None
        assert result.expires_at == datetime(2026, 4, 13, 12, 5, 0)

    def test_get_latest_available_nonce_returns_none(
        self,
        session: Session,
    ) -> None:
        """一致する user_nonce が存在しない場合は None を返すことを検証する。"""
        repository = UserRepository()

        result = repository.get_latest_available_nonce(
            session=session,
            user_id=102,
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert result is None


@pytest.mark.usefixtures("insert_users", "insert_wallets")
class TestCreateUserWallet:
    """create_user_wallet の unit test。"""

    def test_create_user_wallet(
        self,
        session: Session,
    ) -> None:
        """user_wallet を保存し、flush 済みで採番済み ID を取得できることを確認する。"""
        repository = UserRepository()
        user_wallet = UserWallet(
            user_id=102,
            wallet_id=302,
        )

        result = repository.create_user_wallet(session, user_wallet)
        session.expire_all()

        saved_user_wallet = (
            session.query(UserWallet)
            .filter(UserWallet.user_wallet_id == user_wallet.user_wallet_id)
            .one()
        )

        assert result is user_wallet
        assert user_wallet.user_wallet_id is not None
        assert saved_user_wallet.user_wallet_id == user_wallet.user_wallet_id
        assert saved_user_wallet.user_id == 102
        assert saved_user_wallet.wallet_id == 302
        assert saved_user_wallet.created_at is not None
        assert saved_user_wallet.updated_at is not None
        assert saved_user_wallet.deleted_at is None


@pytest.mark.usefixtures("insert_users", "insert_nonces", "insert_user_nonces")
class TestDeleteUserNonceByNonceId:
    def test_delete_user_nonce_by_nonce_id(
        self,
        session: Session,
    ) -> None:
        """存在する nonce_id を指定した場合、対象 UserNonce の deleted_at が設定されること。"""
        repository = UserRepository()
        target_nonce_id = 1

        before = (
            session.query(UserNonce)
            .filter(UserNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_user_nonce_by_nonce_id(session, target_nonce_id)
        session.flush()
        session.expire_all()

        after = (
            session.query(UserNonce)
            .filter(UserNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_user_nonce_by_nonce_id_not_found(
        self,
        session: Session,
    ) -> None:
        """存在しない nonce_id を指定した場合、いずれの UserNonce も更新されないこと。"""
        repository = UserRepository()
        non_existent_nonce_id = 99999

        repository.delete_user_nonce_by_nonce_id(session, non_existent_nonce_id)
        session.flush()
        session.expire_all()

        updated = (
            session.query(UserNonce)
            .filter(UserNonce.deleted_at.isnot(None))
            .all()
        )
        assert len(updated) == 0


@pytest.mark.usefixtures("insert_users", "insert_wallets", "insert_user_wallets")
class TestDeleteUserWalletByWalletId:
    def test_delete_user_wallet_by_wallet_id(
        self,
        session: Session,
    ) -> None:
        """存在する wallet_id を指定した場合、対象 UserWallet の deleted_at が設定されること。"""
        repository = UserRepository()
        target_wallet_id = 301

        before = (
            session.query(UserWallet)
            .filter(UserWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_user_wallet_by_wallet_id(session, target_wallet_id)
        session.flush()
        session.expire_all()

        after = (
            session.query(UserWallet)
            .filter(UserWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_user_wallet_by_wallet_id_not_found(
        self,
        session: Session,
    ) -> None:
        """存在しない wallet_id を指定した場合、いずれの UserWallet も更新されないこと。"""
        repository = UserRepository()
        non_existent_wallet_id = 99999

        before_count = (
            session.query(UserWallet)
            .filter(UserWallet.deleted_at.isnot(None))
            .count()
        )

        repository.delete_user_wallet_by_wallet_id(session, non_existent_wallet_id)
        session.flush()
        session.expire_all()

        after_count = (
            session.query(UserWallet)
            .filter(UserWallet.deleted_at.isnot(None))
            .count()
        )
        assert after_count == before_count
