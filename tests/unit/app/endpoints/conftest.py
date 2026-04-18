from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.endpoints.store import store_router


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(store_router, prefix="/store")

    with TestClient(app) as test_client:
        yield test_client


class _TestDatabase:
    def __init__(self, session: Session) -> None:
        self._session = session

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        yield self._session


@pytest.fixture()
def client_with_db(
    session: Session,
) -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(store_router, prefix="/store")

    test_database = _TestDatabase(session)
    with patch("app.middlewares.transaction.get_db", return_value=test_database):
        with TestClient(app) as test_client:
            yield test_client
