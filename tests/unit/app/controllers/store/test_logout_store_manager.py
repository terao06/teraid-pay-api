"""店舗管理者ログアウトのトランザクションエラーを検証する。"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pymysql.err import IntegrityError as MySQLIntegrityError
from sqlalchemy.exc import IntegrityError, OperationalError

from app.controllers.store_controller import StoreController


class TestLogoutStoreManager:
    """DBトランザクション失敗時のHTTPステータスを検証する。

    Args:
        なし。

    Returns:
        pytestが実行するテストのインスタンス。
    """

    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            (IntegrityError(None, None, MySQLIntegrityError(1062, "duplicate key")), 401),
            (OperationalError(None, None, RuntimeError("commit failed")), 500),
        ],
    )
    def test_commit_failure(self, error: Exception, expected_status: int) -> None:
        """並行登録時の重複は401、その他のコミット失敗は500に変換する。

        Args:
            error: コミット時に発生する例外。
            expected_status: HTTPエラーに変換した後のステータスコード。

        Returns:
            なし。
        """
        with (
            patch("app.controllers.store_controller.get_mysql_db") as get_mysql_db,
            patch("app.controllers.store_controller.StoreAuthService") as service,
        ):
            session = get_mysql_db.return_value.get_session.return_value.__enter__.return_value
            session.begin.return_value.__exit__.side_effect = error
            with pytest.raises(HTTPException) as exception:
                StoreController().logout_store_manager(
                    jti="test-jti", store_manager_id=201, expires_at=datetime(2030, 1, 1)
                )

        service.return_value.logout_store_manager.assert_called_once()
        assert exception.value.status_code == expected_status
        if expected_status == 401:
            assert exception.value.headers == {"WWW-Authenticate": "Bearer"}
