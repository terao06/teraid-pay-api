from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from app.core.aws.secret_manager import SecretManager


class PostgresSQLDatabase:
    """PostgreSQL connection manager."""

    def __init__(self):
        self._engine = None
        self._session_local = None

    def initialize(self):
        """Initialize SQLAlchemy connection settings from Secrets Manager."""
        params = SecretManager().get_secret("secret")

        sqlalchemy_database_url = URL.create(
            "postgresql+psycopg2",
            username=params.get("postgres_user"),
            password=params.get("postgres_password"),
            host=params.get("postgres_host"),
            port=params.get("postgres_port"),
            database=params.get("postgres_database"),
        )

        self._engine = create_engine(
            sqlalchemy_database_url,
            # pool_size=params.get("pool_size"),
            # max_overflow=params.get("max_overflow"),
            # pool_timeout=params.get("pool_timeout"),
            # pool_recycle=params.get("pool_recycle"),
            # pool_pre_ping=params.get("pool_pre_ping"),
        )

        self._session_local = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)

    @property
    def engine(self):
        """Return the SQLAlchemy Engine."""
        if self._engine is None:
            self.initialize()
        return self._engine

    @property
    def session_local(self):
        """Return the SQLAlchemy session factory."""
        if self._session_local is None:
            self.initialize()
        return self._session_local

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Return a SQLAlchemy session as a context manager."""
        if self._session_local is None:
            self.initialize()

        db = self._session_local()
        try:
            yield db
        finally:
            db.close()
