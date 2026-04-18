from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from app.core.aws.secret_manager import SecretManager


Base = declarative_base()


class MySQLDatabase:
    """MySQL 接続を管理するクラスです。"""

    def __init__(self):
        """MySQL 接続管理の初期状態を設定します。
        Args:
            なし: 引数はありません。

        Returns:
            none: 返り値はありません。
        """
        self._engine = None
        self._session_local = None

    def initialize(self):
        """Secrets Manager の情報を使って接続設定を初期化します。
        Args:
            なし: 引数はありません。

        Returns:
            none: 返り値はありません。
        """
        params = SecretManager().get_secret("secret")

        SQLALCHEMY_DATABASE_URL = "mysql+pymysql://{0}:{1}@{2}:{3}/{4}?charset=utf8".format(
            params.get("mysql_user"),
            params.get("mysql_password"),
            params.get("mysql_host"),
            params.get("mysql_port"),
            params.get("mysql_database")
        )

        self._engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            # pool_size=params.get("pool_size"),
            # max_overflow=params.get("max_overflow"),
            # pool_timeout=params.get("pool_timeout"),
            # pool_recycle=params.get("pool_recycle"),
            # pool_pre_ping=params.get("pool_pre_ping"),
        )

        self._session_local = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

    @property
    def engine(self):
        """SQLAlchemy の Engine を取得します。
        Args:
            なし: 引数はありません。

        Returns:
            engine: SQLAlchemy Engine です。
        """
        if self._engine is None:
            self.initialize()
        return self._engine

    @property
    def session_local(self):
        """SQLAlchemy のセッションファクトリを取得します。
        Args:
            なし: 引数はありません。

        Returns:
            session_local: SQLAlchemy のセッションファクトリです。
        """
        if self._session_local is None:
            self.initialize()
        return self._session_local

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """SQLAlchemy のセッションをコンテキスト付きで取得します。
        Args:
            なし: 引数はありません。

        Returns:
            db: 利用可能な SQLAlchemy セッションです。
        """
        if self._session_local is None:
            self.initialize()

        db = self._session_local()
        try:
            yield db
        finally:
            db.close()
