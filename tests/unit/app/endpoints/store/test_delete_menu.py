"""メニュー削除APIのHTTP応答とMySQL上の結果を検証する。"""

from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions.message import MENU_ITEM_NOT_FOUND_ERROR, SERVER_ERROR
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.responses.menu_delete_response import MenuDeleteResponse


class TestDeleteMenu:
    """メニュー削除APIの入力、認証、永続化を検証する。

    Args:
        なし。

    Returns:
        メニュー削除APIのテストケースをまとめたインスタンス。
    """

    @patch("app.endpoints.store.StoreController.delete_menu")
    def test_returns_deleted_menu_id(self, delete_menu, client) -> None:
        """認証店舗の削除処理を委譲し、共通形式で商品IDを返す。

        Args:
            delete_menu: 削除した商品IDを返すControllerのモック。
            client: 店舗管理者の認証情報を設定したクライアント。

        Returns:
            なし。
        """
        delete_menu.return_value = MenuDeleteResponse(menu_item_id=1)

        response = client.delete("/store/menu/1")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": {"menu_item_id": 1}}
        delete_menu.assert_called_once_with(store_id=101, menu_item_id=1)

    @pytest.mark.parametrize("menu_item_id", [0, -1, "invalid"])
    def test_rejects_invalid_id(self, client, menu_item_id) -> None:
        """正の整数以外の商品IDに422を返す。

        Args:
            client: 店舗管理者の認証情報を設定したクライアント。
            menu_item_id: 検証に失敗するパスパラメーター。

        Returns:
            なし。
        """
        response = client.delete(f"/store/menu/{menu_item_id}")

        assert response.status_code == 422
        assert response.json()["detail"][0]["loc"] == ["path", "menu_item_id"]

    def test_requires_authentication(self, client_without_store_manager_auth_override) -> None:
        """JWTを送信していない要求に401とBearer認証ヘッダーを返す。

        Args:
            client_without_store_manager_auth_override: JWT認証を行うクライアント。

        Returns:
            なし。
        """
        response = client_without_store_manager_auth_override.delete("/store/menu/1")

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @patch("app.controllers.store_controller.StoreMenuService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_when_commit_fails(self, mysql_db, service_class, client) -> None:
        """削除サービスの処理後にコミットが失敗したらロールバックして500を返す。

        Args:
            mysql_db: コミット時にDBエラーを送出するセッションのモック。
            service_class: 削除した商品IDを返すサービスのモック。
            client: 店舗管理者の認証情報を設定したクライアント。

        Returns:
            なし。
        """
        session = mysql_db.return_value.get_session.return_value.__enter__.return_value
        session.commit.side_effect = SQLAlchemyError("commit failed")
        service_class.return_value.delete_menu.return_value = MenuDeleteResponse(menu_item_id=1)

        response = client.delete("/store/menu/1")

        assert response.status_code == 500
        assert response.json() == {"detail": {"status": "error", "message": SERVER_ERROR}}
        session.commit.assert_called_once_with()
        session.rollback.assert_called_once_with()

    @pytest.mark.usefixtures("insert_menu_deletion_data")
    @pytest.mark.parametrize(("menu_item_id", "is_available"), [(840001, False), (840002, True)])
    @pytest.mark.parametrize(
        "store_client_with_db", ["menu-mutations-manager@example.com"], indirect=True
    )
    def test_with_db_soft_deletes_menu(
        self, store_client_with_db, mysql_session, menu_item_id, is_available
    ) -> None:
        """販売状態を問わず商品とオプション構成を論理削除する。

        Args:
            store_client_with_db: 実DBで認証済みの店舗管理者クライアント。
            mysql_session: 削除後の行を参照するMySQLセッション。
            menu_item_id: 認証店舗で削除する商品ID。
            is_available: 削除前の商品の販売状態。

        Returns:
            なし。
        """
        path = f"/store/menu/{menu_item_id}"
        response = store_client_with_db.delete(path)

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": {"menu_item_id": menu_item_id}}
        with mysql_session.begin():
            item = mysql_session.get(MenuItem, menu_item_id)
            assert item.deleted_at is not None
            assert item.is_available is is_available
            assert item.image_extension == "png"
            name = item.name
            if menu_item_id == 840001:
                group = mysql_session.get(MenuOptionGroup, 840001)
                option = mysql_session.get(MenuOption, 840001)
                assert group.deleted_at is not None
                assert option.deleted_at is not None
                assert not group.is_active
                assert not option.is_available
                assert mysql_session.get(MenuOptionGroup, 840002).deleted_at == datetime(2026, 2, 1)
                assert mysql_session.get(MenuOption, 840002).deleted_at == datetime(2026, 2, 1)

        assert store_client_with_db.get(path).status_code == 404
        assert store_client_with_db.delete(path).status_code == 404
        listing = store_client_with_db.get("/store/menu", params={"name": name})
        assert listing.status_code == 200
        assert listing.json()["data"]["menu_items"] == []

    @pytest.mark.usefixtures("insert_menu_deletion_data")
    @pytest.mark.parametrize("menu_item_id", [840003, 840004, 840099])
    @pytest.mark.parametrize(
        "store_client_with_db", ["menu-mutations-manager@example.com"], indirect=True
    )
    def test_with_db_rejects_other_store_deleted_or_missing_menu(
        self, store_client_with_db, mysql_session, menu_item_id
    ) -> None:
        """別店舗、削除済み、未存在の商品を404で拒否し、DBを更新しない。

        Args:
            store_client_with_db: 実DBで認証済みの店舗管理者クライアント。
            mysql_session: 削除前後の行を参照するMySQLセッション。
            menu_item_id: 削除を拒否する商品ID。

        Returns:
            なし。
        """
        query = select(MenuItem.deleted_at).where(MenuItem.menu_item_id == menu_item_id)
        with mysql_session.begin():
            before = mysql_session.execute(query).one_or_none()

        response = store_client_with_db.delete(f"/store/menu/{menu_item_id}")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": MENU_ITEM_NOT_FOUND_ERROR}
        }
        with mysql_session.begin():
            assert mysql_session.execute(query).one_or_none() == before
            assert mysql_session.get(MenuOptionGroup, 840003).deleted_at is None
            assert mysql_session.get(MenuOption, 840003).deleted_at is None

    @pytest.mark.usefixtures("insert_menu_deletion_data")
    @pytest.mark.parametrize(
        "store_client_with_db", ["menu-mutations-manager@example.com"], indirect=True
    )
    @patch(
        "app.services.store_menu_service.StoreMenuRepository.soft_delete_menu_item",
        side_effect=SQLAlchemyError("flush failed"),
    )
    def test_with_db_rolls_back_option_deletion_on_item_delete_error(
        self, soft_delete_menu_item, store_client_with_db, mysql_session
    ) -> None:
        """商品の論理削除に失敗した場合、先に反映したグループとオプションの削除を取り消す。

        Args:
            soft_delete_menu_item: 商品の論理削除時にDBエラーを送出するRepositoryメソッド。
            store_client_with_db: 実DBで認証済みの店舗管理者クライアント。
            mysql_session: ロールバック後の行を参照するMySQLセッション。

        Returns:
            なし。
        """
        menu_item_id = 840005
        response = store_client_with_db.delete(f"/store/menu/{menu_item_id}")

        soft_delete_menu_item.assert_called_once()
        assert response.status_code == 500
        assert response.json() == {"detail": {"status": "error", "message": SERVER_ERROR}}
        with mysql_session.begin():
            assert mysql_session.get(MenuItem, menu_item_id).deleted_at is None
            assert mysql_session.get(MenuOptionGroup, 840005).deleted_at is None
            assert mysql_session.get(MenuOption, 840005).deleted_at is None
