from datetime import datetime, timedelta
from decimal import Decimal
import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    MenuImageInvalidException,
    StoreManagerInactiveException,
    StoreNotFoundException,
    UnauthorizedException,
    WalletConflictException,
)
from app.core.config.store_manager_auth import StoreManagerAuthConfig
from app.models.responses.store_manager_login_response import (
    StoreManagerInfoResponse,
    StoreManagerLoginResponse,
)
from app.models.responses.menu_category_response import (
    MenuCategoryListResponse,
    MenuCategoryResponse,
)
from app.models.requests.menu_create_request import (
    MenuCreateRequest,
    MenuOptionCreateRequest,
    MenuOptionGroupCreateRequest,
)
from app.models.responses.menu_create_response import (
    MenuCreateResponse,
    MenuOptionGroupCreateResponse,
)
from app.models.responses.menu_list_response import (
    MenuItemResponse,
    MenuListResponse,
)
from app.models.responses.wallet_response import WalletResponse
from app.models.responses.wallet_nonce_create_response import WalletNonceCreateResponse
from app.models.responses.wallet_nonce_verify_response import WalletVerifyResponse
from app.services.store_service import JST, StoreService


NOW = datetime(2026, 4, 12, 12, 0, 0)


def build_menu_image(format: str = "PNG") -> str:
    """テスト用メニュー画像をBase64文字列で生成する。"""
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestLoginStoreManager:
    """StoreServiceの店舗管理者ログイン処理を検証する。"""

    @patch("app.services.store_service.get_store_manager_auth_config")
    @patch("app.services.store_service.StoreManagerAuthUtil")
    @patch("app.services.store_service.StoreRepository")
    def test_login_store_manager(
        self,
        mock_repository_class,
        mock_auth_util,
        mock_get_auth_config,
    ) -> None:
        """認証成功時にメールアドレスを正規化し、JWTと管理者情報を返すことを検証する。"""
        mysql_session = Mock()
        store_manager = SimpleNamespace(
            store_manager_id=1,
            store_id=101,
            name="店舗管理者",
            email="manager@example.com",
            password_hash="bcrypt-hash",
            roll_id=2,
            is_active=True,
        )
        mock_repository_class.return_value.get_store_manager_by_email.return_value = (
            store_manager
        )
        mock_auth_util.verify_password.return_value = True
        mock_auth_util.create_access_token.return_value = "jwt-token"
        config = StoreManagerAuthConfig(
            jwt_secret="x" * 32,
            access_token_expire_seconds=3600,
        )
        mock_get_auth_config.return_value = config

        result = StoreService().login_store_manager(
            mysql_session=mysql_session,
            email=" Manager@Example.com ",
            password="password123",
        )

        assert result == StoreManagerLoginResponse(
            access_token="jwt-token",
            expires_in=3600,
            store_manager=StoreManagerInfoResponse(
                store_manager_id=1,
                store_id=101,
                name="店舗管理者",
                roll_id=2,
            ),
        )
        mock_repository_class.return_value.get_store_manager_by_email.assert_called_once_with(
            mysql_session=mysql_session,
            email="manager@example.com",
        )
        mock_auth_util.verify_password.assert_called_once_with(
            password="password123",
            password_hash="bcrypt-hash",
        )
        mock_auth_util.create_access_token.assert_called_once_with(
            store_manager=store_manager,
            config=config,
        )

    @patch("app.services.store_service.StoreManagerAuthUtil")
    @patch("app.services.store_service.StoreRepository")
    def test_login_rejects_unknown_email(
        self,
        mock_repository_class,
        mock_auth_util,
    ) -> None:
        """管理者が存在しない場合にダミー照合を実行して認証エラーにすることを検証する。"""
        mock_repository_class.return_value.get_store_manager_by_email.return_value = None

        with pytest.raises(UnauthorizedException):
            StoreService().login_store_manager(
                mysql_session=Mock(),
                email="missing@example.com",
                password="password123",
            )

        mock_auth_util.perform_dummy_password_check.assert_called_once_with(
            "password123"
        )

    @patch("app.services.store_service.StoreManagerAuthUtil")
    @patch("app.services.store_service.StoreRepository")
    def test_login_rejects_inactive_manager(
        self,
        mock_repository_class,
        mock_auth_util,
    ) -> None:
        """パスワードが一致しても無効な管理者はログインできないことを検証する。"""
        store_manager = SimpleNamespace(
            password_hash="bcrypt-hash",
            is_active=False,
        )
        mock_repository_class.return_value.get_store_manager_by_email.return_value = (
            store_manager
        )
        mock_auth_util.verify_password.return_value = True

        with pytest.raises(StoreManagerInactiveException):
            StoreService().login_store_manager(
                mysql_session=Mock(),
                email="inactive@example.com",
                password="password123",
            )


class TestGetStoreWallet:
    @patch("app.services.store_service.StoreRepository")
    def test_get_store_wallet(self, mock_repository_class) -> None:
        mysql_session = Mock()
        store_id = 10
        wallet_info = SimpleNamespace(
            wallet_id=201,
            wallet_address="0x2222222222222222222222222222222222222222",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at=datetime(2024, 2, 10, 12, 0, 0),
            created_at=datetime(2024, 2, 1, 9, 30, 0),
            updated_at=datetime(2024, 2, 15, 18, 45, 0),
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = wallet_info

        result = StoreService().get_store_wallet(mysql_session=mysql_session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        assert result == WalletResponse(
            wallet_id=201,
            wallet_address="0x2222222222222222222222222222222222222222",
            chain_type="ETH",
            network_name="mainnet",
            token_symbol="JPYC",
            chain_id=1,
            is_active=True,
            is_permitted=False,
            verified_at="2024-02-10 12:00",
            created_at="2024-02-01 09:30",
            updated_at="2024-02-15 18:45",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_get_store_wallet_returns_none_when_wallet_not_found(self, mock_repository_class) -> None:
        mysql_session = Mock()
        store_id = 999
        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_wallet.return_value = None

        result = StoreService().get_store_wallet(mysql_session=mysql_session, store_id=store_id)

        mock_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        assert result is None


class TestGetMenuCategories:
    """StoreService のメニューカテゴリー取得処理を検証する。"""

    @patch("app.services.store_service.StoreRepository")
    def test_get_menu_categories(self, mock_repository_class) -> None:
        """取得したカテゴリーを一覧レスポンスへ変換することを確認する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.get_active_menu_categories.return_value = [
            SimpleNamespace(menu_category_id=1, name="ハンバーガー", display_order=1),
            SimpleNamespace(menu_category_id=2, name="ドリンク", display_order=2),
        ]

        result = StoreService().get_menu_categories(
            mysql_session=mysql_session,
            store_id=101,
        )

        assert result == MenuCategoryListResponse(
            menu_categories=[
                MenuCategoryResponse(
                    menu_category_id=1,
                    name="ハンバーガー",
                    display_order=1,
                ),
                MenuCategoryResponse(
                    menu_category_id=2,
                    name="ドリンク",
                    display_order=2,
                ),
            ]
        )
        mock_repository_class.return_value.get_active_menu_categories.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )

    @patch("app.services.store_service.StoreRepository")
    def test_get_menu_categories_returns_empty_list(
        self,
        mock_repository_class,
    ) -> None:
        """カテゴリーが存在しない場合に空の一覧を返すことを確認する。"""
        mock_repository_class.return_value.get_active_menu_categories.return_value = []

        result = StoreService().get_menu_categories(
            mysql_session=Mock(),
            store_id=101,
        )

        assert result == MenuCategoryListResponse(menu_categories=[])


class TestGetMenus:
    """StoreService のメニュー一覧取得処理を検証する。"""

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_get_menus(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """取得した商品とカテゴリー名を一覧レスポンスへ変換することを確認する。"""
        mysql_session = Mock()
        mock_repository_class.return_value.get_menu_items.return_value = [
            (
                SimpleNamespace(
                    menu_item_id=10,
                    menu_category_id=1,
                    name="チーズバーガー",
                    description="チェダーチーズ入り",
                    price=Decimal("800.000000"),
                    token_symbol="JPYC",
                    image_extension="jpeg",
                    is_available=True,
                    display_order=1,
                ),
                "ハンバーガー",
            )
        ]
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
            menu_image_url_expires_in=3600,
        )
        mock_s3_client_class.return_value.generate_presigned_get_url.return_value = (
            "https://s3.example.com/menus/101/10.jpeg"
        )

        result = StoreService().get_menus(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=1,
            is_available=True,
        )

        assert result == MenuListResponse(
            menu_items=[
                MenuItemResponse(
                    menu_item_id=10,
                    menu_category_id=1,
                    menu_category_name="ハンバーガー",
                    name="チーズバーガー",
                    description="チェダーチーズ入り",
                    price="800.000000",
                    token_symbol="JPYC",
                    image_url="https://s3.example.com/menus/101/10.jpeg",
                    is_available=True,
                    display_order=1,
                )
            ]
        )
        mock_repository_class.return_value.get_menu_items.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name="バーガー",
            menu_category_id=1,
            is_available=True,
        )
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        mock_s3_client_class.return_value.generate_presigned_get_url.assert_called_once_with(
            bucket_name="menus",
            file_name="101/10.jpeg",
            expires_in=3600,
        )

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_get_menus_returns_empty_list(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """商品が存在しない場合に空の一覧を返すことを確認する。"""
        mock_repository_class.return_value.get_menu_items.return_value = []
        mysql_session = Mock()

        result = StoreService().get_menus(
            mysql_session=mysql_session,
            store_id=101,
        )

        assert result == MenuListResponse(menu_items=[])
        mock_repository_class.return_value.get_menu_items.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            name=None,
            menu_category_id=None,
            is_available=None,
        )
        mock_ssm_client_class.assert_not_called()
        mock_s3_client_class.assert_not_called()


class TestCreateMenu:
    """StoreService のメニュー登録処理を検証する。"""

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_create_menu(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """商品、オプショングループ、オプションを順番に登録することを確認する。"""
        mysql_session = Mock()
        mysql_session.info = {}
        request = MenuCreateRequest(
            menu_category_id=12,
            name="チーズバーガー",
            description="チェダーチーズ入り",
            price="800.000000",
            token_symbol="JPYC",
            menu_image=build_menu_image(),
            image_extension="png",
            is_available=True,
            display_order=1,
            option_groups=[
                MenuOptionGroupCreateRequest(
                    name="サイズ",
                    min_selections=1,
                    max_selections=1,
                    display_order=1,
                    is_active=True,
                    options=[
                        MenuOptionCreateRequest(
                            name="通常",
                            additional_price="0.000000",
                            display_order=1,
                            is_available=True,
                        ),
                        MenuOptionCreateRequest(
                            name="大盛り",
                            additional_price="100.000000",
                            display_order=2,
                            is_available=True,
                        ),
                    ],
                )
            ],
        )
        mock_repository = mock_repository_class.return_value
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
        )
        mock_s3_client = mock_s3_client_class.return_value
        call_order = []
        mock_repository.get_active_menu_category.return_value = SimpleNamespace(
            menu_category_id=12
        )

        def save_menu_item(mysql_session, menu_item):
            call_order.append("menu_item")
            menu_item.menu_item_id = 10
            return menu_item

        def save_menu_option_group(mysql_session, menu_option_group):
            call_order.append("menu_option_group")
            menu_option_group.menu_option_group_id = 20
            return menu_option_group

        menu_option_ids = iter([30, 31])

        def save_menu_option(mysql_session, menu_option):
            call_order.append("menu_option")
            menu_option.menu_option_id = next(menu_option_ids)
            return menu_option

        mock_repository.create_menu_item.side_effect = save_menu_item
        mock_repository.create_menu_option_group.side_effect = (
            save_menu_option_group
        )
        mock_repository.create_menu_option.side_effect = save_menu_option
        mock_s3_client.upload_object.side_effect = (
            lambda **kwargs: call_order.append("s3_upload")
        )

        result = StoreService().create_menu(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == MenuCreateResponse(
            menu_item_id=10,
            menu_option_groups=[
                MenuOptionGroupCreateResponse(
                    menu_option_group_id=20,
                    menu_option_ids=[30, 31],
                )
            ],
        )
        mock_repository.get_active_menu_category.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
            menu_category_id=12,
        )
        saved_menu_item = mock_repository.create_menu_item.call_args.kwargs[
            "menu_item"
        ]
        assert saved_menu_item.store_id == 101
        assert saved_menu_item.menu_category_id == 12
        assert saved_menu_item.name == "チーズバーガー"
        assert saved_menu_item.price == Decimal("800.000000")
        assert saved_menu_item.image_extension == "png"
        assert mock_repository.create_menu_option_group.call_count == 1
        assert mock_repository.create_menu_option.call_count == 2
        mock_s3_client_class.assert_called_once_with(s3_endpoint="http://s3.local")
        mock_s3_client.upload_object.assert_called_once()
        upload_kwargs = mock_s3_client.upload_object.call_args.kwargs
        assert upload_kwargs["bucket_name"] == "menus"
        assert upload_kwargs["file_name"] == "101/10.png"
        assert upload_kwargs["content_type"] == "image/png"
        assert upload_kwargs["file"].read() != b""
        assert len(mysql_session.info["mysql_rollback_callbacks"]) == 1
        assert call_order == [
            "menu_item",
            "menu_option_group",
            "menu_option",
            "menu_option",
            "s3_upload",
        ]

    @patch("app.services.store_service.S3Client")
    @patch("app.services.store_service.SsmClient")
    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_without_category(
        self,
        mock_repository_class,
        mock_ssm_client_class,
        mock_s3_client_class,
    ) -> None:
        """カテゴリー未指定の場合にカテゴリー検索を行わず登録することを確認する。"""
        request = MenuCreateRequest(
            name="カテゴリーなし商品",
            price="500.000000",
            menu_image=build_menu_image(format="JPEG"),
            image_extension="jpeg",
            option_groups=[],
        )
        mock_repository = mock_repository_class.return_value
        mock_ssm_client_class.return_value = SimpleNamespace(
            s3_endpoint="http://s3.local",
            menu_image_bucket="menus",
        )
        mysql_session = Mock()
        mysql_session.info = {}

        def save_menu_item(mysql_session, menu_item):
            menu_item.menu_item_id = 11
            return menu_item

        mock_repository.create_menu_item.side_effect = save_menu_item

        result = StoreService().create_menu(
            mysql_session=mysql_session,
            store_id=101,
            request=request,
        )

        assert result == MenuCreateResponse(
            menu_item_id=11,
            menu_option_groups=[],
        )
        mock_repository.get_active_menu_category.assert_not_called()
        mock_repository.create_menu_option_group.assert_not_called()
        mock_repository.create_menu_option.assert_not_called()
        mock_s3_client_class.return_value.upload_object.assert_called_once()

    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_raise_when_category_not_found(
        self,
        mock_repository_class,
    ) -> None:
        """有効なカテゴリーが存在しない場合に登録処理を行わないことを確認する。"""
        request = MenuCreateRequest(
            menu_category_id=999,
            name="チーズバーガー",
            price="800.000000",
            menu_image=build_menu_image(),
            image_extension="png",
            option_groups=[],
        )
        mock_repository = mock_repository_class.return_value
        mock_repository.get_active_menu_category.return_value = None

        with pytest.raises(MenuCategoryNotFoundException):
            StoreService().create_menu(
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        mock_repository.create_menu_item.assert_not_called()
        mock_repository.create_menu_option_group.assert_not_called()
        mock_repository.create_menu_option.assert_not_called()

    @patch("app.services.store_service.StoreRepository")
    def test_create_menu_raise_when_menu_image_invalid(
        self,
        mock_repository_class,
    ) -> None:
        """Base64画像と拡張子が一致しない場合にDB登録を行わないことを確認する。"""
        request = MenuCreateRequest(
            name="画像不正商品",
            price="800.000000",
            menu_image=build_menu_image(format="PNG"),
            image_extension="jpeg",
            option_groups=[],
        )

        with pytest.raises(MenuImageInvalidException):
            StoreService().create_menu(
                mysql_session=Mock(),
                store_id=101,
                request=request,
            )

        mock_repository_class.assert_not_called()


class TestCreateWalletNonce:
    """StoreService の create_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_service.secrets.token_urlsafe", return_value="generated-nonce")
    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.NonceRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_create_wallet_nonce(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_store_repository_class,
        mock_token_urlsafe,
    ):
        """nonce を生成して保存し、レスポンスへ整形することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = None

        mock_nonce_repository = mock_nonce_repository_class.return_value
        mock_nonce_repository.create_nonce.side_effect = (
            lambda mysql_session, nonce: SimpleNamespace(nonce_id=123, nonce=nonce.nonce)
        )

        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_called_once_with(32)
        mock_nonce_repository.create_nonce.assert_called_once()
        mock_store_repository.create_store_nonce.assert_called_once()

        nonce_kwargs = mock_nonce_repository.create_nonce.call_args.kwargs
        assert nonce_kwargs["mysql_session"] is mysql_session
        created_nonce = nonce_kwargs["nonce"]
        assert created_nonce.wallet_address == wallet_address.lower()
        assert created_nonce.chain_type == chain_type
        assert created_nonce.network_name == network_name
        assert created_nonce.nonce == "generated-nonce"
        assert created_nonce.expires_at == fixed_now + timedelta(minutes=10)

        store_nonce_kwargs = mock_store_repository.create_store_nonce.call_args.kwargs
        assert store_nonce_kwargs["mysql_session"] is mysql_session
        created_store_nonce = store_nonce_kwargs["store_nonce"]
        assert created_store_nonce.store_id == store_id
        assert created_store_nonce.nonce_id == 123
        assert result == WalletNonceCreateResponse(
            nonce="generated-nonce",
            expires_at="2026-04-12 12:10",
        )

    @patch("app.services.store_service.WalletRepository")
    @patch("app.services.store_service.StoreRepository")
    def test_create_wallet_nonce_not_found_error(
        self,
        mock_repository_class,
        mock_wallet_repository_class,
    ):
        """店舗が存在しない場合に StoreNotFoundException を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 999
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = None

        with pytest.raises(StoreNotFoundException):
            StoreService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository_class.return_value.get_wallet_by_address.assert_not_called()
        mock_repository.create_nonce.assert_not_called()
        mock_repository.create_store_nonce.assert_not_called()

    @patch("app.services.store_service.secrets.token_urlsafe")
    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.NonceRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_create_wallet_nonce_wallet_conflict_error(
        self,
        mock_wallet_repository_class,
        mock_nonce_repository_class,
        mock_store_repository_class,
        mock_token_urlsafe,
    ):
        """ウォレットが既に存在する場合に WalletConflictException を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_by_id.return_value = SimpleNamespace(store_id=store_id)

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.get_wallet_by_address.return_value = SimpleNamespace(wallet_id=1)

        with pytest.raises(WalletConflictException):
            StoreService().create_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_store_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_wallet_repository.get_wallet_by_address.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_address=wallet_address,
        )
        mock_token_urlsafe.assert_not_called()
        mock_nonce_repository_class.return_value.create_nonce.assert_not_called()
        mock_store_repository.create_store_nonce.assert_not_called()


class TestVerifyWalletNonce:
    """StoreService の verify_wallet_nonce を検証するテスト。"""

    @patch("app.services.store_service.WalletUtil.recover_address")
    @patch("app.services.store_service.StoreRepository")
    def test_verify_wallet_nonce(
        self,
        mock_repository_class,
        mock_recover_address,
    ):
        """正常な署名と利用可能 nonce がある場合に nonce エンティティを返すことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"
        nonce_entity = SimpleNamespace(nonce="available-nonce")

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = SimpleNamespace(store_id=10)
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = normalized_wallet_address

        result = StoreService().verify_wallet_nonce(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_address=wallet_address,
            signature=signature,
            chain_type=chain_type,
            network_name=network_name,
        )

        mock_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_repository.get_latest_available_nonce.assert_called_once()
        latest_nonce_kwargs = mock_repository.get_latest_available_nonce.call_args.kwargs
        assert latest_nonce_kwargs["mysql_session"] is mysql_session
        assert latest_nonce_kwargs["store_id"] == store_id
        assert latest_nonce_kwargs["wallet_address"] == normalized_wallet_address
        assert latest_nonce_kwargs["chain_type"] == chain_type
        assert latest_nonce_kwargs["network_name"] == network_name
        assert isinstance(latest_nonce_kwargs["expires_at"], datetime)

        mock_recover_address.assert_called_once_with(
            message=nonce_entity.nonce,
            signature=signature,
        )
        assert result == nonce_entity

    @pytest.mark.parametrize(
        (
            "store",
            "nonce_entity",
            "recovered_address",
            "expected_exception",
        ),
        [
            (
                None,
                SimpleNamespace(nonce="available-nonce"),
                "0xabcdef1234567890abcdef1234567890abcdef12",
                StoreNotFoundException,
            ),
            (
                SimpleNamespace(store_id=10),
                None,
                "0xabcdef1234567890abcdef1234567890abcdef12",
                UnauthorizedException,
            ),
            (
                SimpleNamespace(store_id=10),
                SimpleNamespace(nonce="available-nonce"),
                "0x0000000000000000000000000000000000000000",
                UnauthorizedException,
            ),
        ],
        ids=[
            "store-not-found",
            "nonce-not-found",
            "signature-mismatch",
        ],
    )
    @patch("app.services.store_service.WalletUtil.recover_address")
    @patch("app.services.store_service.StoreRepository")
    def test_verify_wallet_nonce_raises(
        self,
        mock_repository_class,
        mock_recover_address,
        store,
        nonce_entity,
        recovered_address,
        expected_exception,
    ):
        """異常系では条件に応じた例外を送出することを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        signature = "signed-message"
        chain_type = "ethereum"
        network_name = "sepolia"

        mock_repository = mock_repository_class.return_value
        mock_repository.get_store_by_id.return_value = store
        mock_repository.get_latest_available_nonce.return_value = nonce_entity
        mock_recover_address.return_value = recovered_address

        with pytest.raises(expected_exception):
            StoreService().verify_wallet_nonce(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                signature=signature,
                chain_type=chain_type,
                network_name=network_name,
            )

        mock_repository.get_store_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )

        if store is None:
            mock_repository.get_latest_available_nonce.assert_not_called()
            mock_recover_address.assert_not_called()
            return

        mock_repository.get_latest_available_nonce.assert_called_once()

        if nonce_entity is None:
            mock_recover_address.assert_not_called()
            return

        mock_recover_address.assert_called_once_with(
            message=nonce_entity.nonce,
            signature=signature,
        )


class TestCreateStoreWallet:
    """StoreService の create_store_wallet を検証するテスト。"""

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    @patch("app.services.store_service.NonceRepository")
    def test_create_store_wallet(self, mock_nonce_repository_class, mock_wallet_repository_class, mock_store_repository_class):
        """primary の切り替えと nonce の使用済み更新を行い、レスポンスを返すことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        normalized_wallet_address = wallet_address.lower()
        chain_type = "ethereum"
        network_name = "sepolia"
        token_symbol = "JPYC"
        chain_id = 11155111
        fixed_now = datetime(2026, 4, 12, 12, 34, 56)
        nonce_entity = SimpleNamespace(nonce_id=1, used_at=None)

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_wallet_by_store_id.return_value = None
        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_wallet_repository.create_wallet.return_value = SimpleNamespace(wallet_id=77)

        mock_nonce_repository = mock_nonce_repository_class.return_value


        with patch("app.services.store_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_now

            result = StoreService().create_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_store_repository.get_wallet_by_store_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )

        mock_wallet_repository.create_wallet.assert_called_once()
        create_wallet_kwargs = mock_wallet_repository.create_wallet.call_args.kwargs
        assert create_wallet_kwargs["mysql_session"] is mysql_session
        created_wallet = create_wallet_kwargs["wallet"]
        assert created_wallet.wallet_address == normalized_wallet_address
        assert created_wallet.chain_type == chain_type
        assert created_wallet.network_name == network_name
        assert created_wallet.token_symbol == token_symbol
        assert created_wallet.chain_id == chain_id
        assert created_wallet.verified_at == fixed_now
        assert created_wallet.is_active is True
        assert created_wallet.is_permitted is True

        mock_store_repository.create_store_wallet.assert_called_once()
        create_store_wallet_kwargs = mock_store_repository.create_store_wallet.call_args.kwargs
        assert create_store_wallet_kwargs["mysql_session"] is mysql_session
        created_store_wallet = create_store_wallet_kwargs["store_wallet"]
        assert created_store_wallet.store_id == store_id
        assert created_store_wallet.wallet_id == 77

        mock_nonce_repository.update_nonce.assert_called_once_with(
            mysql_session=mysql_session,
            nonce=nonce_entity,
        )
        assert nonce_entity.used_at == fixed_now
        assert result == WalletVerifyResponse(
            wallet_address=normalized_wallet_address,
            chain_type=chain_type,
            network_name=network_name,
            token_symbol=token_symbol,
            chain_id=chain_id,
            is_active=True,
            is_permitted=True,
            verified_at="2026-04-12 12:34",
        )

    @patch("app.services.store_service.StoreRepository")
    def test_create_store_wallet_conflict(self, mock_repository_class):
        """同一チェーン・ネットワークに同じウォレットが存在する場合は競合例外を送出する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        chain_type = "ethereum"
        network_name = "sepolia"
        token_symbol = "JPYC"
        chain_id = 11155111
        nonce_entity = SimpleNamespace(used_at=None)

        mock_repository = mock_repository_class.return_value
        mock_repository.get_wallet_by_store_id.return_value = SimpleNamespace(wallet_id=99)

        with pytest.raises(WalletConflictException):
            StoreService().create_store_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_address=wallet_address,
                chain_type=chain_type,
                network_name=network_name,
                token_symbol=token_symbol,
                chain_id=chain_id,
                nonce_entity=nonce_entity,
            )

        mock_repository.get_wallet_by_store_id.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            chain_type=chain_type,
            network_name=network_name,
            chain_id=chain_id,
        )
        mock_repository.create_wallet.assert_not_called()
        mock_repository.create_store_wallet.assert_not_called()
        mock_repository.update_nonce.assert_not_called()
        assert nonce_entity.used_at is None


class TestDeleteWallet:
    """StoreService の delete_wallet を検証するテスト。"""

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_delete_wallet(self, mock_wallet_repository_class, mock_store_repository_class):
        """WalletRepository と StoreRepository の各削除メソッドが正しい引数で呼ばれることを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet_link.return_value = Mock()

        StoreService().delete_wallet(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )

        mock_store_repository.get_store_wallet_link.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
            wallet_id=wallet_id,
        )
        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )

    @patch("app.services.store_service.StoreRepository")
    @patch("app.services.store_service.WalletRepository")
    def test_delete_wallet_store_repository_not_called_when_wallet_repository_raises(
        self,
        mock_wallet_repository_class,
        mock_store_repository_class,
    ):
        """WalletRepositoryが例外を送出した場合、StoreRepositoryの削除処理を呼ばないことを検証する。"""
        mysql_session = Mock()
        store_id = 10
        wallet_id = 42

        mock_wallet_repository = mock_wallet_repository_class.return_value
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet_link.return_value = Mock()
        mock_wallet_repository.delete_wallet_by_wallet_id.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            StoreService().delete_wallet(
                mysql_session=mysql_session,
                store_id=store_id,
                wallet_id=wallet_id,
            )

        mock_wallet_repository.delete_wallet_by_wallet_id.assert_called_once_with(
            mysql_session=mysql_session,
            wallet_id=wallet_id,
        )
        mock_store_repository.delete_store_wallet_by_wallet_id.assert_not_called()
