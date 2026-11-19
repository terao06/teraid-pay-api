"""メニュー削除Controllerのトランザクションと例外変換を検証する。"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.store_controller import StoreController
from app.core.exceptions.custom_exception import MenuItemNotFoundException
from app.core.exceptions.message import MENU_ITEM_NOT_FOUND_ERROR
from app.models.responses.menu_delete_response import MenuDeleteResponse


@patch("app.controllers.store_controller.StoreMenuService")
@patch("app.middlewares.transaction.get_mysql_db")
def test_commits_successful_deletion(mysql_db, service_class) -> None:
    """サービスに認証店舗IDと商品IDを渡し、成功時にコミットする。

    Args:
        mysql_db: トランザクション用DB接続のモック。
        service_class: 削除結果を返すサービスのモック。

    Returns:
        なし。
    """
    session = mysql_db.return_value.get_session.return_value.__enter__.return_value
    service = service_class.return_value.delete_menu
    service.return_value = MenuDeleteResponse(menu_item_id=1)

    result = StoreController().delete_menu(store_id=101, menu_item_id=1)

    assert result == service.return_value
    service.assert_called_once_with(mysql_session=session, store_id=101, menu_item_id=1)
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@patch("app.controllers.store_controller.StoreMenuService")
@patch("app.middlewares.transaction.get_mysql_db")
def test_rolls_back_and_maps_missing_menu_to_not_found(mysql_db, service_class) -> None:
    """対象が見つからない場合はロールバックして共通形式の404に変換する。

    Args:
        mysql_db: トランザクション用DB接続のモック。
        service_class: 商品未存在の例外を送出するサービスのモック。

    Returns:
        なし。
    """
    session = mysql_db.return_value.get_session.return_value.__enter__.return_value
    service_class.return_value.delete_menu.side_effect = MenuItemNotFoundException()

    with pytest.raises(HTTPException) as exc_info:
        StoreController().delete_menu(store_id=101, menu_item_id=1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == {"status": "error", "message": MENU_ITEM_NOT_FOUND_ERROR}
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


@patch("app.controllers.store_controller.StoreMenuService")
@patch("app.middlewares.transaction.get_mysql_db")
def test_rolls_back_and_propagates_database_error(mysql_db, service_class) -> None:
    """DBエラーをロールバックし、元の例外をエンドポイントに伝える。

    Args:
        mysql_db: トランザクション用DB接続のモック。
        service_class: DBエラーを送出するサービスのモック。

    Returns:
        なし。
    """
    session = mysql_db.return_value.get_session.return_value.__enter__.return_value
    error = SQLAlchemyError("flush failed")
    service_class.return_value.delete_menu.side_effect = error

    with pytest.raises(SQLAlchemyError) as exc_info:
        StoreController().delete_menu(store_id=101, menu_item_id=1)

    assert exc_info.value is error
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
