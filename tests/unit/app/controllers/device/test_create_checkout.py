"""会計作成ControllerのコミットとHTTP例外変換を検証する。"""

from contextlib import nullcontext
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.controllers.device_controller import DeviceController
from app.core.exceptions.custom_exception import (
    DeviceCheckoutConflictException,
    UnauthorizedException,
    VisitSessionNotFoundException,
)
from app.core.exceptions.message import DEVICE_CHECKOUT_PROCESSING_ERROR
from app.models.responses.device_checkout_create_response import DeviceCheckoutCreateResponse


REQUEST_ARGS = {
    "device_uuid": "90100100-0000-4000-8000-000000901001",
    "visit_session_id": 902001,
}


class TestCreateCheckout:
    """会計作成のトランザクションとHTTPエラーを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    def test_commits_and_returns_service_result(self) -> None:
        """会計作成成功時にコミットし、Serviceからの結果を返す。

        Args:
            なし。

        Returns:
            なし。
        """
        session = Mock(spec=Session, info={})
        result = DeviceCheckoutCreateResponse(checkout_id=1, orders=[], total_amount="300.000000", token_symbol="JPYC")
        with (
            patch("app.middlewares.transaction.get_mysql_db") as get_db,
            patch("app.controllers.device_controller.DeviceOrderService") as service,
        ):
            get_db.return_value.get_session.return_value = nullcontext(session)
            service.return_value.create_checkout.return_value = result
            assert DeviceController().create_checkout(**REQUEST_ARGS) == result
        service.return_value.create_checkout.assert_called_once_with(mysql_session=session, **REQUEST_ARGS)
        session.commit.assert_called_once_with()
        session.rollback.assert_not_called()

    @pytest.mark.parametrize(("error", "status", "headers"), [
        (UnauthorizedException(), 401, {"WWW-Authenticate": "Bearer"}),
        (VisitSessionNotFoundException(), 404, None),
        (DeviceCheckoutConflictException(DEVICE_CHECKOUT_PROCESSING_ERROR), 409, None),
        (RuntimeError("db failed"), 500, None),
        (None, 500, None),
    ])
    def test_translates_errors_and_rolls_back(self, error, status, headers) -> None:
        """業務、DB、コミットの失敗をHTTPエラーに変換し、ロールバックする。

        Args:
            error: Serviceの例外。Noneの場合はコミットを失敗させる。
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
            service.return_value.create_checkout.side_effect = error
            with pytest.raises(HTTPException) as failure:
                DeviceController().create_checkout(**REQUEST_ARGS)
        assert failure.value.status_code == status
        assert failure.value.headers == headers
        assert failure.value.detail.keys() == {"status", "message"}
        session.rollback.assert_called_once_with()
        assert session.commit.call_count == (1 if error is None else 0)
