from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.aws.secret_manager import SecretManager
from app.endpoints.store import store_router
from app.endpoints.user import user_router
from app.middlewares.transaction import get_db


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_with_db(
) -> Generator[TestClient, None, None]:
    get_db.cache_clear()

    app = FastAPI()
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")

    with patch.object(
        SecretManager,
        "get_secret",
        return_value={
            "mysql_user": "teraid_pay_admin_user",
            "mysql_password": "password",
            "mysql_host": "127.0.0.1",
            "mysql_port": "3307",
            "mysql_database": "db_local",
        },
    ):
        with TestClient(app) as test_client:
            yield test_client

    get_db.cache_clear()
