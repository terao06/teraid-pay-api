"""カテゴリー別メニュー取得Serviceの業務分岐と画像URL生成を検証する。"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import DEFAULT, Mock, call, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import (
    MenuCategoryNotFoundException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.models.mysql.device import Device
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.services.device_service import DeviceService


DEVICE_UUID = "81006600-0000-4000-8000-000000000066"
DEVICE_ID = 810066
STORE_ID = 110
VISIT_SESSION_ID = 820066
CATEGORY_ID = 830012


@pytest.fixture()
def menu_dependencies():
    """利用可能な端末と来店セッションを既定値とする依存先を用意する。

    Args:
        なし。

    Yields:
        端末、来店、メニュー、画像設定、画像署名のモック。
    """
    with patch.multiple(
        "app.services.device_service",
        DeviceRepository=DEFAULT,
        VisitSessionRepository=DEFAULT,
        StoreMenuRepository=DEFAULT,
        SsmClient=DEFAULT,
        S3Client=DEFAULT,
    ) as mocks:
        device = mocks["DeviceRepository"].return_value
        device.get_device_by_uuid.return_value = Device(
            device_id=DEVICE_ID, store_id=STORE_ID, activated_at=datetime(2026, 1, 1), is_active=True,
        )
        mocks["VisitSessionRepository"].return_value.has_active_visit_session.return_value = True
        yield mocks


class TestGetMenuItemsByCategory:
    """取得条件とレスポンスの組み立てを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_rejects_unavailable_device_before_loading_menu(self, menu_dependencies) -> None:
        """利用できない端末をセッションやメニューの参照前に拒否する。

        Args:
            menu_dependencies: Repositoryと画像関連クライアントのモック。

        Returns:
            なし。
        """
        devices = menu_dependencies["DeviceRepository"].return_value
        devices.get_device_by_uuid.return_value.is_active = False

        with pytest.raises(UnauthorizedException):
            DeviceService().get_menu_items_by_category(Mock(spec=Session), DEVICE_UUID, VISIT_SESSION_ID, CATEGORY_ID)

        menu_dependencies["VisitSessionRepository"].assert_not_called()
        menu_dependencies["StoreMenuRepository"].assert_not_called()
        menu_dependencies["SsmClient"].assert_not_called()

    def test_rejects_unavailable_visit_before_loading_menu(self, menu_dependencies) -> None:
        """自端末の注文受付中セッションがなければメニューを参照しない。

        Args:
            menu_dependencies: Repositoryと画像関連クライアントのモック。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        visits = menu_dependencies["VisitSessionRepository"].return_value
        visits.has_active_visit_session.return_value = False

        with pytest.raises(VisitSessionNotFoundException):
            DeviceService().get_menu_items_by_category(session, DEVICE_UUID, VISIT_SESSION_ID, CATEGORY_ID)

        visits.has_active_visit_session.assert_called_once_with(
            mysql_session=session, device_id=DEVICE_ID, visit_session_id=VISIT_SESSION_ID,
        )
        menu_dependencies["StoreMenuRepository"].assert_not_called()
        menu_dependencies["SsmClient"].assert_not_called()

    def test_rejects_missing_category_before_signing(self, menu_dependencies) -> None:
        """カテゴリーが見つからなければ画像設定を取得せず例外を送出する。

        Args:
            menu_dependencies: Repositoryと画像関連クライアントのモック。

        Returns:
            なし。
        """
        repository = menu_dependencies["StoreMenuRepository"].return_value
        repository.get_menu_items_by_category.return_value = []

        with pytest.raises(MenuCategoryNotFoundException):
            DeviceService().get_menu_items_by_category(Mock(spec=Session), DEVICE_UUID, VISIT_SESSION_ID, CATEGORY_ID)

        menu_dependencies["SsmClient"].assert_not_called()

    def test_returns_empty_menu_without_signing(self, menu_dependencies) -> None:
        """有効なカテゴリーに販売可能な商品がなければ空配列を返す。

        Args:
            menu_dependencies: Repositoryと画像関連クライアントのモック。

        Returns:
            なし。
        """
        repository = menu_dependencies["StoreMenuRepository"].return_value
        repository.get_menu_items_by_category.return_value = [(CATEGORY_ID, None, None, None)]

        result = DeviceService().get_menu_items_by_category(Mock(spec=Session), DEVICE_UUID, VISIT_SESSION_ID, CATEGORY_ID)

        assert result.model_dump() == {"menu_items": []}
        menu_dependencies["SsmClient"].assert_not_called()
        menu_dependencies["S3Client"].assert_not_called()

    def test_groups_join_rows_and_signs_once_per_item(self, menu_dependencies) -> None:
        """結合で繰り返す親をまとめ、商品ごとに一度だけ画像URLを署名する。

        Args:
            menu_dependencies: Repositoryと画像関連クライアントのモック。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        repository = menu_dependencies["StoreMenuRepository"].return_value
        first = MenuItem(
            menu_item_id=5, name="Burger", price=Decimal("650.25"), token_symbol="JPYC", image_extension="jpeg",
            display_order=1,
        )
        second = MenuItem(
            menu_item_id=4, name="Fries", price=Decimal("300"), token_symbol="JPYC", image_extension="png",
            display_order=2,
        )
        group = MenuOptionGroup(
            menu_option_group_id=10, name="Toppings", min_selections=0, max_selections=2, display_order=1,
        )
        empty_group = MenuOptionGroup(
            menu_option_group_id=11, name="Sauces", min_selections=0, max_selections=1, display_order=2,
        )
        first_option = MenuOption(menu_option_id=21, name="Cheese", additional_price=Decimal("100.5"), display_order=1)
        second_option = MenuOption(menu_option_id=20, name="Lettuce", additional_price=Decimal("50"), display_order=2)
        repository.get_menu_items_by_category.return_value = [
            (CATEGORY_ID, first, group, first_option),
            (CATEGORY_ID, first, group, second_option),
            (CATEGORY_ID, first, empty_group, None),
            (CATEGORY_ID, second, None, None),
        ]
        params = menu_dependencies["SsmClient"].return_value
        params.s3_endpoint = "http://s3.example.com"
        params.menu_image_bucket = "menus"
        params.menu_image_url_expires_in = 3600
        sign = menu_dependencies["S3Client"].return_value.generate_presigned_get_url
        sign.side_effect = ["https://example.com/5.jpeg", "https://example.com/4.png"]

        result = DeviceService().get_menu_items_by_category(session, DEVICE_UUID, VISIT_SESSION_ID, CATEGORY_ID)

        repository.get_menu_items_by_category.assert_called_once_with(
            mysql_session=session, store_id=STORE_ID, menu_category_id=CATEGORY_ID,
        )
        item, no_groups_item = result.menu_items
        assert (item.menu_item_id, item.price, item.image_url) == (5, "650.250000", "https://example.com/5.jpeg")
        assert (no_groups_item.menu_item_id, no_groups_item.option_groups) == (4, [])
        with_options, without_options = item.option_groups
        assert with_options.menu_option_group_id == 10
        assert [(option.menu_option_id, option.additional_price) for option in with_options.options] == [
            (21, "100.500000"), (20, "50.000000"),
        ]
        assert (without_options.menu_option_group_id, without_options.options) == (11, [])
        menu_dependencies["SsmClient"].assert_called_once_with()
        menu_dependencies["S3Client"].assert_called_once_with(s3_endpoint=params.s3_endpoint)
        assert sign.call_args_list == [
            call(bucket_name="menus", file_name="110/5.jpeg", expires_in=3600),
            call(bucket_name="menus", file_name="110/4.png", expires_in=3600),
        ]
