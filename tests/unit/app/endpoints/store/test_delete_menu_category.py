"""メニューカテゴリー削除APIの入力検証とDB操作を確認する。"""

from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions.message import MENU_CATEGORY_NOT_FOUND_ERROR, SERVER_ERROR
from app.models.responses.menu_category_response import MenuCategoryDeleteResponse


class TestDeleteMenuCategory:
    """カテゴリー削除APIのHTTP応答とDB上の結果を検証する。

    Args:
        なし。

    Returns:
        カテゴリー削除APIのテストケースをまとめたインスタンス。
    """

    @patch("app.endpoints.store.StoreController.delete_menu_category")
    def test_returns_deleted_category_id(self, mock_delete_menu_category, client) -> None:
        """認証店舗のカテゴリー削除を委譲し、共通形式で削除IDを返す。

        Args:
            mock_delete_menu_category: 削除したカテゴリーIDを返すControllerのモック。
            client: 店舗管理者認証を差し替えたテストクライアント。

        Returns:
            なし。
        """
        mock_delete_menu_category.return_value = MenuCategoryDeleteResponse(menu_category_id=1)

        response = client.delete("/store/menu/categories/1")

        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": {"menu_category_id": 1}}
        mock_delete_menu_category.assert_called_once_with(store_id=101, menu_category_id=1)

    @pytest.mark.parametrize("menu_category_id", [0, -1, "invalid"])
    def test_rejects_invalid_id(self, client, menu_category_id) -> None:
        """正の整数以外のカテゴリーIDには422を返す。

        Args:
            client: 店舗管理者認証を差し替えたテストクライアント。
            menu_category_id: 検証に失敗させるパスパラメーター。

        Returns:
            なし。
        """
        response = client.delete(f"/store/menu/categories/{menu_category_id}")

        assert response.status_code == 422

    def test_requires_authentication(self, client_without_store_manager_auth_override) -> None:
        """JWTがない削除リクエストには401を返す。

        Args:
            client_without_store_manager_auth_override: JWT認証を実行するテストクライアント。

        Returns:
            なし。
        """
        response = client_without_store_manager_auth_override.delete("/store/menu/categories/1")

        assert response.status_code == 401

    @patch("app.controllers.store_controller.StoreMenuCategoryService")
    @patch("app.middlewares.transaction.get_mysql_db")
    def test_rolls_back_on_commit_error(self, mysql_db, service_class, client) -> None:
        """コミット失敗時はトランザクションをロールバックして500を返す。

        Args:
            mysql_db: コミットが失敗するDB接続を設定するモック。
            service_class: 削除成功を返すサービスクラスのモック。
            client: 店舗管理者認証を差し替えたテストクライアント。

        Returns:
            なし。
        """
        session = mysql_db.return_value.get_session.return_value.__enter__.return_value
        session.commit.side_effect = SQLAlchemyError("commit failed")
        service_class.return_value.delete_menu_category.return_value = MenuCategoryDeleteResponse(
            menu_category_id=1
        )

        response = client.delete("/store/menu/categories/1")

        assert response.status_code == 500
        assert response.json() == {"detail": {"status": "error", "message": SERVER_ERROR}}
        session.commit.assert_called_once_with()
        session.rollback.assert_called_once_with()

    @pytest.mark.usefixtures("insert_menu_category_deletion_data")
    @pytest.mark.parametrize(("menu_category_id", "is_active"), [(830001, True), (830002, False)])
    def test_with_db_soft_deletes_category(
        self, store_client_with_db, mysql_engine, menu_category_id, is_active
    ) -> None:
        """有効状態を問わず論理削除し、商品の紐づけを保持する。

        Args:
            store_client_with_db: 実DBで認証済みの店舗管理者クライアント。
            mysql_engine: 削除後のカテゴリーと商品の行を参照するMySQL Engine。
            menu_category_id: 認証店舗で削除するカテゴリーID。
            is_active: 削除前のカテゴリーの有効状態。

        Returns:
            なし。
        """
        path = f"/store/menu/categories/{menu_category_id}"

        response = store_client_with_db.delete(path)

        assert response.status_code == 200
        assert response.json() == {
            "status": "success", "data": {"menu_category_id": menu_category_id}
        }
        with mysql_engine.connect() as connection:
            category = connection.execute(
                text(
                    "SELECT is_active, deleted_at FROM menu_categories "
                    "WHERE menu_category_id = :menu_category_id"
                ),
                {"menu_category_id": menu_category_id},
            ).one()
            item = connection.execute(
                text(
                    "SELECT menu_category_id, deleted_at FROM menu_items WHERE menu_item_id = 830001"
                )
            ).one()
        assert bool(category.is_active) is is_active
        assert category.deleted_at is not None
        assert item.menu_category_id == 830001
        assert item.deleted_at is None
        assert store_client_with_db.get(path).status_code == 404
        assert store_client_with_db.delete(path).status_code == 404

    @pytest.mark.usefixtures("insert_menu_category_deletion_data")
    @pytest.mark.parametrize("menu_category_id", [830003, 830004, 830099])
    def test_with_db_rejects_other_store_deleted_or_missing_category(
        self, store_client_with_db, mysql_engine, menu_category_id
    ) -> None:
        """別店舗、削除済み、未存在のカテゴリーに404を返す。

        Args:
            store_client_with_db: 実DBで認証済みの店舗管理者クライアント。
            mysql_engine: 削除前後のカテゴリーの行を参照するMySQL Engine。
            menu_category_id: 削除を拒否するカテゴリーID。

        Returns:
            なし。
        """
        query = text(
            "SELECT deleted_at FROM menu_categories WHERE menu_category_id = :menu_category_id"
        )
        parameters = {"menu_category_id": menu_category_id}
        with mysql_engine.connect() as connection:
            before = connection.execute(query, parameters).one_or_none()

        response = store_client_with_db.delete(f"/store/menu/categories/{menu_category_id}")

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": MENU_CATEGORY_NOT_FOUND_ERROR}
        }
        with mysql_engine.connect() as connection:
            after = connection.execute(query, parameters).one_or_none()
        assert after == before
