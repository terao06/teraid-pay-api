"""メニュー削除Serviceのロック順序と論理削除を検証する。"""

from unittest.mock import Mock, call, patch

import pytest

from app.core.exceptions.custom_exception import MenuItemNotFoundException
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.services.store_menu_service import StoreMenuService


@patch("app.services.store_menu_service.S3Client")
@patch("app.services.store_menu_service.StoreMenuRepository")
def test_locks_and_soft_deletes_menu_with_options(repository_class, s3_client_class) -> None:
    """商品から順に排他ロックし、オプションから順に論理削除して画像を保持する。

    Args:
        repository_class: 対象の取得と更新の順序を記録するRepositoryのモック。
        s3_client_class: 画像へのアクセスを検出するS3クライアントのモック。

    Returns:
        なし。
    """
    session = Mock()
    item = MenuItem(menu_item_id=1, is_available=False, image_extension="png")
    group = MenuOptionGroup(menu_option_group_id=2, menu_item_id=1)
    option = MenuOption(menu_option_id=3, menu_option_group_id=2)
    repository = repository_class.return_value
    repository.get_menu_item.return_value = item
    repository.get_menu_option_groups.return_value = [group]
    repository.get_menu_options.return_value = [option]

    result = StoreMenuService().delete_menu(mysql_session=session, store_id=101, menu_item_id=1)

    assert result.menu_item_id == 1
    assert item.is_available is False
    assert item.image_extension == "png"
    assert repository.mock_calls == [
        call.get_menu_item(
            mysql_session=session, store_id=101, menu_item_id=1, lock_for_update=True
        ),
        call.get_menu_option_groups(
            mysql_session=session, menu_item_id=1, lock_for_update=True
        ),
        call.get_menu_options(
            mysql_session=session, menu_option_group_ids=[2], lock_for_update=True
        ),
        call.soft_delete_menu_option(mysql_session=session, menu_option=option),
        call.soft_delete_menu_option_group(mysql_session=session, menu_option_group=group),
        call.soft_delete_menu_item(mysql_session=session, menu_item=item),
    ]
    s3_client_class.assert_not_called()


@patch("app.services.store_menu_service.StoreMenuRepository")
def test_missing_menu_stops_before_loading_children(repository_class) -> None:
    """対象商品が見つからない場合は関連行の取得や書き込みを行わない。

    Args:
        repository_class: 商品が見つからない状態を返すRepositoryのモック。

    Returns:
        なし。
    """
    session = Mock()
    repository = repository_class.return_value
    repository.get_menu_item.return_value = None

    with pytest.raises(MenuItemNotFoundException):
        StoreMenuService().delete_menu(mysql_session=session, store_id=101, menu_item_id=1)

    assert repository.mock_calls == [
        call.get_menu_item(
            mysql_session=session, store_id=101, menu_item_id=1, lock_for_update=True
        )
    ]
