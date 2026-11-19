"""メニューカテゴリー削除Serviceのロックと論理削除を検証する。"""

from unittest.mock import Mock, call, patch

import pytest

from app.core.exceptions.custom_exception import MenuCategoryNotFoundException
from app.models.mysql.menu_category import MenuCategory
from app.services.store_menu_category_service import StoreMenuCategoryService


@patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
def test_locks_category_before_soft_deleting(repository_class) -> None:
    """店舗条件で対象を排他ロックしてからRepositoryの論理削除を呼ぶ。

    Args:
        repository_class: 削除対象と論理削除の呼び出しを確認するRepositoryのモック。

    Returns:
        なし。
    """
    category = MenuCategory(menu_category_id=1, deleted_at=None)
    repository = repository_class.return_value
    repository.get_menu_category_detail.return_value = category
    session = Mock()

    result = StoreMenuCategoryService().delete_menu_category(
        mysql_session=session, store_id=101, menu_category_id=1
    )

    assert result.menu_category_id == 1
    assert repository.mock_calls == [
        call.get_menu_category_detail(
            mysql_session=session, store_id=101, menu_category_id=1, lock_for_update=True
        ),
        call.soft_delete_menu_category(mysql_session=session, menu_category=category),
    ]


@patch("app.services.store_menu_category_service.StoreMenuCategoryRepository")
def test_missing_category_does_not_write(repository_class) -> None:
    """削除対象が見つからない場合は例外を送出し、論理削除を呼び出さない。

    Args:
        repository_class: 対象カテゴリーが見つからない状態を返すRepositoryのモック。

    Returns:
        なし。
    """
    repository = repository_class.return_value
    repository.get_menu_category_detail.return_value = None

    with pytest.raises(MenuCategoryNotFoundException):
        StoreMenuCategoryService().delete_menu_category(
            mysql_session=Mock(), store_id=101, menu_category_id=999
        )

    repository.soft_delete_menu_category.assert_not_called()
