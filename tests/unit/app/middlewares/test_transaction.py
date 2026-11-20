"""MySQLトランザクションの補償処理と例外ログを検証する。"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions.message import SERVER_ERROR
from app.middlewares.transaction import (
    add_mysql_rollback_callback,
    mysql_transaction,
)


class TestMysqlTransactionRollbackCallback:
    """MySQLトランザクションの補償処理を検証する。"""

    @patch("app.middlewares.transaction.get_mysql_db")
    def test_runs_callback_when_commit_fails(self, mock_get_mysql_db, caplog) -> None:
        """コミット失敗時にロールバック後の補償処理を実行することを確認する。"""
        mysql_session = (
            mock_get_mysql_db.return_value.get_session.return_value
            .__enter__.return_value
        )
        mysql_session.info = {}
        mysql_session.commit.side_effect = RuntimeError("commit error")
        callback = Mock()

        @mysql_transaction
        def target(mysql_session):
            add_mysql_rollback_callback(
                mysql_session=mysql_session,
                callback=callback,
            )

        with pytest.raises(RuntimeError, match="commit error"):
            target()

        mysql_session.rollback.assert_called_once_with()
        callback.assert_called_once_with()
        assert "Error during transaction: commit error" in caplog.text

    @patch("app.middlewares.transaction.get_mysql_db")
    def test_discards_callback_when_commit_succeeds(self, mock_get_mysql_db) -> None:
        """コミット成功時は補償処理を実行せず登録情報を破棄することを確認する。"""
        mysql_session = (
            mock_get_mysql_db.return_value.get_session.return_value
            .__enter__.return_value
        )
        mysql_session.info = {}
        callback = Mock()

        @mysql_transaction
        def target(mysql_session):
            add_mysql_rollback_callback(
                mysql_session=mysql_session,
                callback=callback,
            )
            return "success"

        result = target()

        assert result == "success"
        mysql_session.commit.assert_called_once_with()
        callback.assert_not_called()
        assert mysql_session.info == {}


@patch("app.middlewares.transaction.get_mysql_db")
def test_mysql_transaction_suppresses_error_details_when_configured(mock_get_mysql_db, caplog) -> None:
    """例外メッセージをログに記録せず、コミット失敗時はロールバックする。

    Args:
        mock_get_mysql_db: MySQL接続のモック。
        caplog: テスト中のログを取得するpytestフィクスチャ。

    Returns:
        なし。
    """
    session = mock_get_mysql_db.return_value.get_session.return_value.__enter__.return_value
    session.info = {}
    error = RuntimeError("test-confidential-value")
    session.commit.side_effect = error

    @mysql_transaction(log_error_details=False)
    def target(mysql_session):
        """トランザクション内でMySQLセッションを受け取る。"""
        assert mysql_session is session

    with pytest.raises(RuntimeError) as caught:
        target()

    assert caught.value is error
    session.rollback.assert_called_once_with()
    assert str(error) not in caplog.text


@patch("app.middlewares.transaction.get_mysql_db")
def test_mysql_transaction_converts_commit_failure_to_http_500(mock_get_mysql_db, caplog) -> None:
    """コミット失敗をロールバックし、共通形式のHTTP 500に変換する。

    Args:
        mock_get_mysql_db: MySQL接続のモック。
        caplog: テスト中のログを取得するpytestフィクスチャ。

    Returns:
        なし。
    """
    session = mock_get_mysql_db.return_value.get_session.return_value.__enter__.return_value
    session.info = {}
    session.commit.side_effect = RuntimeError("test-confidential-value")

    @mysql_transaction(log_error_details=False, http_500_on_error=True)
    def target(mysql_session):
        """トランザクション内でMySQLセッションを受け取る。"""
        assert mysql_session is session

    with pytest.raises(HTTPException) as caught:
        target()

    session.rollback.assert_called_once_with()
    assert caught.value.status_code == 500
    assert caught.value.detail == {"status": "error", "message": SERVER_ERROR}
    assert "RuntimeError" in caplog.text
    assert "test-confidential-value" not in caplog.text
