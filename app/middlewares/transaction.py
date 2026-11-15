from functools import wraps, lru_cache
import logging
from collections.abc import Callable
from app.core.database.mysql import MySQLDatabase
from app.core.database.postgres import PostgresSQLDatabase

logger = logging.getLogger(__name__)
MYSQL_ROLLBACK_CALLBACKS_KEY = "mysql_rollback_callbacks"


def add_mysql_rollback_callback(
    mysql_session,
    callback: Callable[[], None],
) -> None:
    """MySQLトランザクション失敗時に実行する補償処理を登録する。

    Args:
        mysql_session: 補償処理を紐づけるSQLAlchemyセッション。
        callback: ロールバック後に実行する補償処理。

    Returns:
        なし。
    """
    mysql_session.info.setdefault(MYSQL_ROLLBACK_CALLBACKS_KEY, []).append(callback)


def _run_mysql_rollback_callbacks(session) -> None:
    """登録済みのMySQLロールバック補償処理を逆順で実行する。"""
    callbacks = session.info.pop(MYSQL_ROLLBACK_CALLBACKS_KEY, [])
    for callback in reversed(callbacks):
        try:
            callback()
        except Exception:
            logger.exception("Error during MySQL rollback compensation")


@lru_cache()
def get_mysql_db():
    """データベース接続を管理するオブジェクトを取得します。
    Args:
        なし: 引数はありません。

    Returns:
        database: MySQLDatabase のインスタンスです。
    """
    return MySQLDatabase()


@lru_cache()
def get_postgres_db():
    """データベース接続を管理するオブジェクトを取得します。
    Args:
        なし: 引数はありません。

    Returns:
        database: POSTGRESDatabase のインスタンスです。
    """
    return PostgresSQLDatabase()


def mysql_transaction(func):
    """トランザクション付きで関数を実行するデコレータを生成します。
    Args:
        func: トランザクション管理の対象となる関数です。

    Returns:
        wrapper: トランザクション管理を付与した関数です。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """トランザクション制御の中で対象関数を実行します。
        Args:
            args: 対象関数に渡す位置引数です。
            kwargs: 対象関数に渡すキーワード引数です。

        Returns:
            result: 対象関数の実行結果です。
        """
        with get_mysql_db().get_session() as session:
            try:
                kwargs['mysql_session'] = session
                result = func(*args, **kwargs)
                session.commit()
                session.info.pop(MYSQL_ROLLBACK_CALLBACKS_KEY, None)
                return result
            except Exception as e:
                session.rollback()
                _run_mysql_rollback_callbacks(session)
                logger.error(f"Error during transaction: {e}")
                raise

    return wrapper


def postgres_transaction(func):
    """トランザクション付きで関数を実行するデコレータを生成します。
    Args:
        func: トランザクション管理の対象となる関数です。

    Returns:
        wrapper: トランザクション管理を付与した関数です。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """トランザクション制御の中で対象関数を実行します。
        Args:
            args: 対象関数に渡す位置引数です。
            kwargs: 対象関数に渡すキーワード引数です。

        Returns:
            result: 対象関数の実行結果です。
        """
        with get_postgres_db().get_session() as session:
            try:
                kwargs['postgres_session'] = session
                result = func(*args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"Error during transaction: {e}")
                raise

    return wrapper
