from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.aws.secret_manager import SecretManager
from app.endpoints.face import face_router
from app.endpoints.payment import payment_router
from app.endpoints.store import store_router
from app.endpoints.user import user_router
from app.middlewares.transaction import get_mysql_db, get_postgres_db
from tests.unit.test_data.secret.insert_secret import insert_secret


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(payment_router, prefix="/payment")
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")
    app.include_router(face_router, prefix="/face")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_with_db(
) -> Generator[TestClient, None, None]:

    app = FastAPI()
    app.include_router(payment_router, prefix="/payment")
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")
    app.include_router(face_router, prefix="/face")

    with patch.object(
        SecretManager,
        "get_secret",
        return_value={
            "mysql_user": "teraid_pay_admin_user",
            "mysql_password": "password",
            "mysql_host": "127.0.0.1",
            "mysql_port": "3307",
            "mysql_database": "db_local",
            "postgres_database": "vector_db",
            "postgres_user": "vector_user",
            "postgres_password": "vector_password",
            "postgres_host": "127.0.0.1",
            "postgres_port": 5432,
            "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/hogehoge",
            "chain_1_jpyc_token_address": "0x2222222222222222222222222222222222222222",
            "chain_1_payment_processor_address": "0x3333333333333333333333333333333333333333",
            "chain_1_payment_operator_private_key": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "chain_11155111_jpyc_token_address": "0x4444444444444444444444444444444444444444",
            "chain_11155111_payment_processor_address": "0x5555555555555555555555555555555555555555",
            "chain_11155111_payment_operator_private_key": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
    ):
        with TestClient(app) as test_client:
            yield test_client

    get_mysql_db.cache_clear()
    get_postgres_db.cache_clear()
    insert_secret()
