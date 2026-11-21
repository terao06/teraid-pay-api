"""注文登録Controllerのコミット、ロールバック、例外変換を検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import (
    DeviceOrderConflictException,
    DeviceOrderInvalidException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.models.requests.device_order_create_request import DeviceOrderCreateRequest
from app.models.responses.device_order_create_response import DeviceOrderCreateResponse


_REQUEST = DeviceOrderCreateRequest(items=[{"menu_item_id": 1, "quantity": 2, "options": []}])
_REQUEST_ARGS = {
    "device_uuid": "88100100-0000-4000-8000-000000881001",
    "visit_session_id": 882001,
    "idempotency_key": "order-key",
    "request": _REQUEST,
}


class TestCreateOrder:
    """注文登録の処理結果とHTTPエラーをトランザクション単位で検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("created", [True, False])
    def test_commits_and_returns_service_result(self, created) -> None:
        """保存結果をコミットし、Serviceから渡された新規登録フラグを返す。

        Args:
            created: 新規登録された場合のフラグ。

        Returns:
            なし。
        """
        session = Mock(spec=Session, info={})
        result = DeviceOrderCreateResponse(menu_order_id=1, total_amount="600.000000", token_symbol="JPYC"), created
        with (
            patch("app.middlewares.transaction.get_mysql_db") as get_db,
            patch("app.controllers.device_controller.DeviceOrderService") as service,
        ):
            get_db.return_value.get_session.return_value = nullcontext(session)
            service.return_value.create_order.return_value = result
            assert DeviceController().create_order(**_REQUEST_ARGS) == result
        service.return_value.create_order.assert_called_once_with(mysql_session=session, **_REQUEST_ARGS)
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(("error", "status", "headers"), [
        (UnauthorizedException(), 401, {"WWW-Authenticate": "Bearer"}),
        (VisitSessionNotFoundException(), 404, None),
        (DeviceOrderConflictException(), 409, None),
        (DeviceOrderInvalidException(), 422, None),
        (RuntimeError("db failed"), 500, None),
        (None, 500, None),
    ])
    def test_rolls_back_and_translates_errors(self, error, status, headers) -> None:
        """業務例外とDB・コミットの失敗をHTTPエラーに変換し、ロールバックする。

        Args:
            error: Serviceの例外。Noneの場合はコミットで失敗させる。
            status: 期待するHTTPステータス。
            headers: 期待するHTTPヘッダー。

        Returns:
            なし。
        """
        session = Mock(spec=Session, info={})
        if error is None:
            session.commit.side_effect = RuntimeError("commit failed")
        with (
            patch("app.middlewares.transaction.get_mysql_db") as get_db,
            patch("app.controllers.device_controller.DeviceOrderService") as service,
        ):
            get_db.return_value.get_session.return_value = nullcontext(session)
            service.return_value.create_order.side_effect = error
            with pytest.raises(HTTPException) as failure:
                DeviceController().create_order(**_REQUEST_ARGS)
        assert failure.value.status_code == status
        assert failure.value.headers == headers
        assert failure.value.detail.keys() == {"status", "message"}
        session.rollback.assert_called_once_with()
        assert session.commit.call_count == (1 if error is None else 0)
