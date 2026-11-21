"""オーダー一覧コントローラーの呼び出しと失敗応答を検証する。"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.controllers.store_controller import StoreController
from app.core.exceptions.message import SERVER_ERROR
from app.models.mysql.menu_order import OrderFulfillmentStatus
from app.models.responses.order_list_response import OrderListResponse, OrderListPaginationResponse


class TestGetOrders:
    """オーダー一覧のトランザクションとサービス呼び出しを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @patch("app.middlewares.transaction.get_mysql_db")
    @patch("app.controllers.store_controller.StoreOrderService")
    def test_returns_service_result(self, mock_service_class, mock_database) -> None:
        """所属店舗とページ条件をサービスに渡し、処理結果を返す。

        Args:
            mock_service_class: サービスのモック。
            mock_database: MySQL セッション提供処理のモック。

        Returns:
            なし。
        """
        session = mock_database.return_value.get_session.return_value.__enter__.return_value
        service = mock_service_class.return_value
        expected = OrderListResponse(
            orders=[], pagination=OrderListPaginationResponse(page=2, page_size=10, total=0, total_pages=0)
        )
        service.get_orders.return_value = expected

        result = StoreController().get_orders(store_id=101, fulfillment_status=OrderFulfillmentStatus.SERVED, page=2, page_size=10)

        assert result == expected
        service.get_orders.assert_called_once_with(mysql_session=session, store_id=101, fulfillment_status=OrderFulfillmentStatus.SERVED, page=2, page_size=10)
        session.commit.assert_called_once_with()

    @patch("app.middlewares.transaction.get_mysql_db")
    @patch("app.controllers.store_controller.StoreOrderService")
    def test_converts_db_error_to_500(self, mock_service_class, mock_database) -> None:
        """DB 参照に失敗した場合はロールバックし HTTP 500 を返す。

        Args:
            mock_service_class: サービスのモック。
            mock_database: MySQL セッション提供処理のモック。

        Returns:
            なし。
        """
        session = mock_database.return_value.get_session.return_value.__enter__.return_value
        mock_service_class.return_value.get_orders.side_effect = SQLAlchemyError("query failed")

        with pytest.raises(HTTPException) as error:
            StoreController().get_orders(store_id=101, fulfillment_status=OrderFulfillmentStatus.UNSERVED, page=1, page_size=20)

        assert error.value.status_code == 500
        assert error.value.detail == {"status": "error", "message": SERVER_ERROR}
        session.rollback.assert_called_once_with()
