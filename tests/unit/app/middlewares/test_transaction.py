from unittest.mock import Mock, patch

import pytest

from app.middlewares.transaction import (
    add_mysql_rollback_callback,
    mysql_transaction,
)


class TestMysqlTransactionRollbackCallback:
    """MySQLトランザクションの補償処理を検証する。"""

    @patch("app.middlewares.transaction.get_mysql_db")
    def test_runs_callback_when_commit_fails(self, mock_get_mysql_db) -> None:
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
