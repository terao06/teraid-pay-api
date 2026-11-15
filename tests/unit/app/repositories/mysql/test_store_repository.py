from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.nonce import Nonce
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.wallet import Wallet
from app.repositories.mysql.nonce_repository import NonceRepository
from app.repositories.mysql.store_repository import StoreRepository
from app.repositories.mysql.wallet_repository import WalletRepository


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetStoreWallet:
    @pytest.mark.parametrize(
        ("store_id", "expected_wallet"),
        [
            (
                101,
                {
                    "wallet_id": 301,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "sepolia",
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
            (
                101,
                {
                    "wallet_id": 301,
                    "wallet_address": "0x1111111111111111111111111111111111111111",
                    "chain_type": "ETH",
                    "network_name": "sepolia",
                    "is_active": True,
                    "verified_at": "2024-01-10 12:00:00",
                },
            ),
        ],
    )
    def test_get_store_wallet(
        self,
        mysql_session: Session,
        store_id: int | None,
        expected_wallet: dict,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_store_wallet(mysql_session, store_id)

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
        mysql_session: Session,
        store_id: int,
        expected_store_id: int | None,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_store_by_id(mysql_session, store_id)

        if expected_store_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_id == expected_store_id


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetActiveMenuCategories:
    """店舗の有効なメニューカテゴリー取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_menu_category_ids"),
        [
            (101, [12, 13, 11]),
            (104, []),
        ],
    )
    def test_get_active_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
        expected_menu_category_ids: list[int],
    ) -> None:
        """店舗に紐づく有効かつ未削除のカテゴリーを表示順で取得することを確認する。"""
        repository = StoreRepository()

        result = repository.get_active_menu_categories(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        assert [category.menu_category_id for category in result] == (
            expected_menu_category_ids
        )


@pytest.mark.usefixtures("insert_menu_categories")
class TestGetActiveMenuCategory:
    """店舗の有効なメニューカテゴリー1件取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "menu_category_id", "expected_menu_category_id"),
        [
            (101, 12, 12),
            (101, 14, None),
            (101, 15, None),
            (101, 16, None),
            (102, 16, 16),
        ],
    )
    def test_get_active_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
        expected_menu_category_id: int | None,
    ) -> None:
        """店舗、ID、有効状態、削除状態に一致するカテゴリーだけを取得することを確認する。"""
        result = StoreRepository().get_active_menu_category(
            mysql_session=mysql_session,
            store_id=store_id,
            menu_category_id=menu_category_id,
        )

        if expected_menu_category_id is None:
            assert result is None
            return

        assert result is not None
        assert result.menu_category_id == expected_menu_category_id


@pytest.mark.usefixtures("insert_menu_items")
class TestGetMenuItems:
    """店舗のメニュー商品一覧取得を検証する。"""

    @pytest.mark.parametrize(
        ("store_id", "expected_menu_items"),
        [
            (
                101,
                [
                    (21, "フード"),
                    (22, "ドリンク"),
                    (23, None),
                    (24, None),
                ],
            ),
            (104, []),
        ],
    )
    def test_get_menu_items(
        self,
        mysql_session: Session,
        store_id: int,
        expected_menu_items: list[tuple[int, str | None]],
    ) -> None:
        """店舗の未削除商品と未削除カテゴリー名を表示順で取得することを確認する。"""
        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        actual_menu_items = [
            (menu_item.menu_item_id, menu_category_name)
            for menu_item, menu_category_name in result
        ]
        if store_id == 104:
            assert actual_menu_items == expected_menu_items
            return

        fixture_menu_items = [
            menu_item
            for menu_item in actual_menu_items
            if menu_item[0] in {21, 22, 23, 24}
        ]
        assert fixture_menu_items == expected_menu_items
        assert 25 not in [menu_item[0] for menu_item in actual_menu_items]
        assert 26 not in [menu_item[0] for menu_item in actual_menu_items]

    @pytest.mark.parametrize(
        ("filters", "expected_ids"),
        [
            ({"menu_category_id": 12}, [21]),
            ({"is_available": False}, [22]),
            (
                {
                    "menu_category_id": 12,
                    "is_available": True,
                },
                [21],
            ),
        ],
    )
    def test_get_menu_items_with_filters(
        self,
        mysql_session: Session,
        filters: dict[str, object],
        expected_ids: list[int],
    ) -> None:
        """商品名・カテゴリー・公開状態を組み合わせて検索できることを確認する。"""
        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=101,
            **filters,
        )

        assert [menu_item.menu_item_id for menu_item, _ in result] == expected_ids

    def test_get_menu_items_with_partial_name(
        self,
        mysql_session: Session,
    ) -> None:
        """商品名の一部を指定して検索できることを確認する。"""
        menu_name = (
            mysql_session.query(MenuItem.name)
            .filter(MenuItem.menu_item_id == 22)
            .scalar()
        )
        assert menu_name is not None

        result = StoreRepository().get_menu_items(
            mysql_session=mysql_session,
            store_id=101,
            name=menu_name,
        )

        assert [menu_item.menu_item_id for menu_item, _ in result] == [22]


@pytest.mark.usefixtures("insert_stores", "insert_menu_categories")
class TestCreateMenu:
    """メニュー商品、オプショングループ、オプションの登録を検証する。"""

    def test_create_menu(
        self,
        mysql_session: Session,
    ) -> None:
        """商品、オプショングループ、オプションへIDを付与して保存することを確認する。"""
        repository = StoreRepository()
        menu_item = MenuItem(
            store_id=101,
            menu_category_id=12,
            name="リポジトリテスト商品",
            description="商品説明",
            price=Decimal("800.000000"),
            token_symbol="JPYC",
            image_extension="jpg",
            is_available=True,
            display_order=1,
        )

        saved_menu_item = repository.create_menu_item(
            mysql_session=mysql_session,
            menu_item=menu_item,
        )
        saved_menu_option_group = repository.create_menu_option_group(
            mysql_session=mysql_session,
            menu_option_group=MenuOptionGroup(
                menu_item_id=saved_menu_item.menu_item_id,
                name="サイズ",
                min_selections=1,
                max_selections=1,
                display_order=1,
                is_active=True,
            ),
        )
        saved_menu_option = repository.create_menu_option(
            mysql_session=mysql_session,
            menu_option=MenuOption(
                menu_option_group_id=(
                    saved_menu_option_group.menu_option_group_id
                ),
                name="大盛り",
                additional_price=Decimal("100.000000"),
                display_order=1,
                is_available=True,
            ),
        )

        stored_menu_item = (
            mysql_session.query(MenuItem)
            .filter(MenuItem.menu_item_id == saved_menu_item.menu_item_id)
            .one()
        )
        stored_menu_option_group = (
            mysql_session.query(MenuOptionGroup)
            .filter(
                MenuOptionGroup.menu_option_group_id
                == saved_menu_option_group.menu_option_group_id
            )
            .one()
        )
        stored_menu_option = (
            mysql_session.query(MenuOption)
            .filter(MenuOption.menu_option_id == saved_menu_option.menu_option_id)
            .one()
        )

        assert stored_menu_item.store_id == 101
        assert stored_menu_item.menu_category_id == 12
        assert stored_menu_item.price == Decimal("800.000000")
        assert stored_menu_item.image_extension == "jpg"
        assert stored_menu_option_group.menu_item_id == stored_menu_item.menu_item_id
        assert stored_menu_option_group.min_selections == 1
        assert stored_menu_option_group.max_selections == 1
        assert (
            stored_menu_option.menu_option_group_id
            == stored_menu_option_group.menu_option_group_id
        )
        assert stored_menu_option.additional_price == Decimal("100.000000")


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestGetWalletByStoreId:
    @pytest.mark.parametrize(
        ("store_id", "chain_type", "network_name", "chain_id", "expected_wallet_id"),
        [
            (101, "ETH", "sepolia", 11155111, 301),
            (101, "ETH", "mainnet", 1, None),
            (101, "ETH", "goerli", 1, None),
            (102, "ETH", "sepolia", 11155111, 304),
            (999, "ETH", "mainnet", 1, None),
        ],
    )
    def test_get_wallet_by_store_id(
        self,
        mysql_session: Session,
        store_id: int,
        chain_type: str,
        network_name: str,
        chain_id: int,
        expected_wallet_id: int | None,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_wallet_by_store_id(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )

        if expected_wallet_id is None:
            assert result is None
            return

        assert result is not None
        assert result.wallet_id == expected_wallet_id
        assert result.chain_type == chain_type
        assert result.network_name == network_name
        assert result.chain_id == chain_id


@pytest.mark.usefixtures("insert_stores")
class TestCreateStoreNonce:
    def test_create_store_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()
        nonce = Nonce(
            wallet_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            chain_type="ethereum",
            network_name="sepolia",
            nonce="test-store-wallet-nonce",
            expires_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        saved_nonce = NonceRepository().create_nonce(mysql_session, nonce)

        store_nonce = StoreNonce(store_id=101, nonce_id=saved_nonce.nonce_id)
        repository.create_store_nonce(mysql_session, store_nonce)
        mysql_session.flush()

        saved_store_nonce = (
            mysql_session.query(StoreNonce)
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
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()
        new_wallet = Wallet(
            wallet_address="0xcccccccccccccccccccccccccccccccccccccccc",
            chain_type="ethereum",
            network_name="sepolia",
            token_symbol="JPYC",
            chain_id=11155111,
            is_active=True,
            verified_at=datetime(2026, 4, 13, 12, 0, 0),
        )
        saved_wallet = WalletRepository().create_wallet(mysql_session, new_wallet)

        store_wallet = StoreWallet(
            store_id=101,
            wallet_id=saved_wallet.wallet_id,
        )

        repository.create_store_wallet(mysql_session, store_wallet)
        mysql_session.flush()

        saved_store_wallet = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == saved_wallet.wallet_id)
            .one()
        )

        assert saved_store_wallet.store_wallet_id is not None
        assert saved_store_wallet.store_id == 101
        assert saved_store_wallet.wallet_id == saved_wallet.wallet_id
        assert saved_store_wallet.created_at is not None
        assert saved_store_wallet.updated_at is not None
        assert saved_store_wallet.deleted_at is None


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestGetLatestAvailableNonce:
    def test_get_latest_available_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()
        base_expires_at = datetime(2026, 4, 13, 12, 0, 0)

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
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
        mysql_session: Session,
    ) -> None:
        repository = StoreRepository()

        result = repository.get_latest_available_nonce(
            mysql_session=mysql_session,
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
        mysql_session: Session,
    ) -> None:
        """存在する nonce_id を指定した場合、対象 StoreNonce の deleted_at が設定されること。"""
        repository = StoreRepository()
        target_nonce_id = 8

        before = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_store_nonce_by_nonce_id(mysql_session, target_nonce_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_store_nonce_by_nonce_id_not_found(
        self,
        mysql_session: Session,
    ) -> None:
        """存在しない nonce_id を指定した場合、いずれの StoreNonce も更新されないこと。"""
        repository = StoreRepository()
        non_existent_nonce_id = 99999
        before_count = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .count()
        )

        repository.delete_store_nonce_by_nonce_id(mysql_session, non_existent_nonce_id)
        mysql_session.flush()
        mysql_session.expire_all()

        updated = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .all()
        )
        assert len(updated) == before_count


@pytest.mark.usefixtures("insert_stores", "insert_wallets", "insert_store_wallets")
class TestDeleteStoreWalletByWalletId:
    def test_delete_store_wallet_by_wallet_id(
        self,
        mysql_session: Session,
    ) -> None:
        """存在する wallet_id を指定した場合、対象 StoreWallet の deleted_at と updated_at が設定されること。"""
        repository = StoreRepository()
        target_wallet_id = 312

        before = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_store_wallet_by_wallet_id(mysql_session, target_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.wallet_id == target_wallet_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_store_wallet_by_wallet_id_not_found(
        self,
        mysql_session: Session,
    ) -> None:
        """存在しない wallet_id を指定した場合、いずれの StoreWallet も更新されないこと。"""
        repository = StoreRepository()
        non_existent_wallet_id = 99999

        before_count = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.deleted_at.isnot(None))
            .count()
        )

        repository.delete_store_wallet_by_wallet_id(mysql_session, non_existent_wallet_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after_count = (
            mysql_session.query(StoreWallet)
            .filter(StoreWallet.deleted_at.isnot(None))
            .count()
        )
        assert after_count == before_count
