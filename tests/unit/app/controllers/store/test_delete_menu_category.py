"""メニューカテゴリー削除Controllerの例外変換とロールバックを検証する。"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import MenuCategoryNotFoundException
from app.core.exceptions.message import MENU_CATEGORY_NOT_FOUND_ERROR


@patch("app.controllers.store_controller.StoreMenuCategoryService")
def test_maps_missing_category_to_not_found(service_class) -> None:
    """対象の未存在を共通形式の404に変換する。

    Args:
        service_class: 対象未存在の例外を送出するカテゴリーサービスのモック。

    Returns:
        なし。
    """
    service_class.return_value.delete_menu_category.side_effect = MenuCategoryNotFoundException()

    with pytest.raises(HTTPException) as exc_info:
        StoreController.delete_menu_category.__wrapped__(
            StoreController(), mysql_session=Mock(), store_id=101, menu_category_id=999
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == {"status": "error", "message": MENU_CATEGORY_NOT_FOUND_ERROR}


@patch("app.controllers.store_controller.StoreMenuCategoryService")
@patch("app.middlewares.transaction.get_mysql_db")
def test_rolls_back_when_delete_fails(mysql_db, service_class) -> None:
    """削除処理中のDBエラーでトランザクションを打ち切る。

    Args:
        mysql_db: トランザクションで使用するDB接続のモック。
        service_class: DBエラーを送出するカテゴリーサービスのモック。

    Returns:
        なし。
    """
    session = mysql_db.return_value.get_session.return_value.__enter__.return_value
    error = SQLAlchemyError("flush failed")
    service_class.return_value.delete_menu_category.side_effect = error

    with pytest.raises(SQLAlchemyError) as exc_info:
        StoreController().delete_menu_category(store_id=101, menu_category_id=1)

    assert exc_info.value is error
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
