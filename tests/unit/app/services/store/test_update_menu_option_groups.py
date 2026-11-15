"""メニューオプション構成更新Serviceのテスト。"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.core.exceptions.custom_exception import (
    MenuItemNotFoundException,
    MenuOptionConfigurationInvalidException,
)
from app.models.requests.menu_option_groups_update_request import (
    MenuOptionGroupUpdateRequest,
    MenuOptionGroupsUpdateRequest,
    MenuOptionUpdateRequest,
)
from app.models.responses.menu_option_groups_update_response import (
    MenuOptionGroupsUpdateResponse,
    MenuOptionGroupUpdateResult,
)
from app.services.store_menu_service import StoreMenuService


def _build_request() -> MenuOptionGroupsUpdateRequest:
    """更新・追加・削除を含むテスト用リクエストを生成する。

    Returns:
        テスト用メニューオプション構成更新リクエスト。
    """
    return MenuOptionGroupsUpdateRequest(
        option_groups=[
            MenuOptionGroupUpdateRequest(
                menu_option_group_id=20,
                name="更新サイズ",
                min_selections=1,
                max_selections=1,
                display_order=1,
                is_active=True,
                options=[
                    MenuOptionUpdateRequest(
                        menu_option_id=30,
                        name="更新通常",
                        additional_price=Decimal("10.000000"),
                        display_order=1,
                        is_available=True,
                    ),
                    MenuOptionUpdateRequest(
                        name="特大",
                        additional_price=Decimal("200.000000"),
                        display_order=2,
                        is_available=True,
                    ),
                ],
            ),
            MenuOptionGroupUpdateRequest(
                name="トッピング",
                min_selections=0,
                max_selections=2,
                display_order=2,
                is_active=True,
                options=[],
            ),
        ]
    )


class TestUpdateMenuOptionGroups:
    """StoreMenuServiceのオプション構成完全同期を検証する。"""

    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_synchronizes_option_groups(self, mock_repository_class) -> None:
        """既存行を更新し、新規行を追加して、除外行を論理削除する。"""
        mysql_session = Mock()
        existing_group = SimpleNamespace(
            menu_option_group_id=20,
            menu_item_id=10,
            name="サイズ",
            min_selections=1,
            max_selections=1,
            display_order=1,
            is_active=True,
        )
        removed_group = SimpleNamespace(
            menu_option_group_id=21,
            menu_item_id=10,
        )
        existing_option = SimpleNamespace(
            menu_option_id=30,
            menu_option_group_id=20,
            name="通常",
            additional_price=Decimal("0.000000"),
            display_order=1,
            is_available=True,
        )
        removed_option = SimpleNamespace(
            menu_option_id=31,
            menu_option_group_id=20,
        )
        removed_group_option = SimpleNamespace(
            menu_option_id=40,
            menu_option_group_id=21,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_item.return_value = SimpleNamespace(
            menu_item_id=10
        )
        repository.get_menu_option_groups.return_value = [
            existing_group,
            removed_group,
        ]
        repository.get_menu_options.return_value = [
            existing_option,
            removed_option,
            removed_group_option,
        ]
        repository.save_menu_option_group.side_effect = (
            lambda mysql_session, menu_option_group: menu_option_group
        )
        repository.save_menu_option.side_effect = (
            lambda mysql_session, menu_option: menu_option
        )

        def create_group(mysql_session, menu_option_group):
            """新規グループへテスト用IDを付与する。"""
            if menu_option_group.menu_option_group_id is None:
                menu_option_group.menu_option_group_id = 22
            return menu_option_group

        def create_option(mysql_session, menu_option):
            """新規オプションへテスト用IDを付与する。"""
            if menu_option.menu_option_id is None:
                menu_option.menu_option_id = 32
            return menu_option

        repository.save_menu_option_group.side_effect = create_group
        repository.save_menu_option.side_effect = create_option

        result = StoreMenuService().update_menu_option_groups(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
            request=_build_request(),
        )

        assert result == MenuOptionGroupsUpdateResponse(
            menu_item_id=10,
            menu_option_groups=[
                MenuOptionGroupUpdateResult(
                    menu_option_group_id=20,
                    menu_option_ids=[30, 32],
                ),
                MenuOptionGroupUpdateResult(
                    menu_option_group_id=22,
                    menu_option_ids=[],
                ),
            ],
        )
        assert existing_group.name == "更新サイズ"
        assert existing_option.name == "更新通常"
        assert repository.soft_delete_menu_option.call_count == 2
        repository.soft_delete_menu_option_group.assert_called_once_with(
            mysql_session=mysql_session,
            menu_option_group=removed_group,
        )

    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_rejects_option_owned_by_another_group(
        self,
        mock_repository_class,
    ) -> None:
        """異なるグループに属する既存オプションIDを拒否する。"""
        repository = mock_repository_class.return_value
        repository.get_menu_item.return_value = SimpleNamespace(
            menu_item_id=10
        )
        repository.get_menu_option_groups.return_value = [
            SimpleNamespace(menu_option_group_id=20),
            SimpleNamespace(menu_option_group_id=21),
        ]
        repository.get_menu_options.return_value = [
            SimpleNamespace(menu_option_id=30, menu_option_group_id=21)
        ]
        request = _build_request()

        with pytest.raises(MenuOptionConfigurationInvalidException):
            StoreMenuService().update_menu_option_groups(
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=10,
                request=request,
            )

        repository.save_menu_option_group.assert_not_called()

    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_rejects_inaccessible_menu_item(self, mock_repository_class) -> None:
        """認証店舗に属さない商品は更新しない。"""
        repository = mock_repository_class.return_value
        repository.get_menu_item.return_value = None

        with pytest.raises(MenuItemNotFoundException):
            StoreMenuService().update_menu_option_groups(
                mysql_session=Mock(),
                store_id=101,
                menu_item_id=999,
                request=MenuOptionGroupsUpdateRequest(option_groups=[]),
            )

        repository.get_menu_option_groups.assert_not_called()

    @patch("app.services.store_menu_service.StoreMenuRepository")
    def test_empty_groups_soft_deletes_all_options(
        self,
        mock_repository_class,
    ) -> None:
        """空の構成を指定した場合は既存グループとオプションを全削除する。"""
        mysql_session = Mock()
        group = SimpleNamespace(menu_option_group_id=20)
        option = SimpleNamespace(
            menu_option_id=30,
            menu_option_group_id=20,
        )
        repository = mock_repository_class.return_value
        repository.get_menu_item.return_value = SimpleNamespace(
            menu_item_id=10
        )
        repository.get_menu_option_groups.return_value = [group]
        repository.get_menu_options.return_value = [option]

        result = StoreMenuService().update_menu_option_groups(
            mysql_session=mysql_session,
            store_id=101,
            menu_item_id=10,
            request=MenuOptionGroupsUpdateRequest(option_groups=[]),
        )

        assert result == MenuOptionGroupsUpdateResponse(
            menu_item_id=10,
            menu_option_groups=[],
        )
        repository.soft_delete_menu_option.assert_called_once_with(
            mysql_session=mysql_session,
            menu_option=option,
        )
        repository.soft_delete_menu_option_group.assert_called_once_with(
            mysql_session=mysql_session,
            menu_option_group=group,
        )
