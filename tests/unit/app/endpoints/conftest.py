from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.aws.secret_manager import SecretManager
from app.dependencies.store_manager_auth import (
    StoreManagerAuthContext,
    authenticate_store_manager,
)
from app.endpoints.face import face_router
from app.endpoints.payment import payment_router
from app.endpoints.store import store_router
from app.endpoints.user import user_router
from app.middlewares.transaction import get_mysql_db, get_postgres_db
from tests.unit.test_data.secret.insert_secret import insert_secret


def override_store_manager_auth() -> StoreManagerAuthContext:
    """既存endpointテスト用に店舗管理者の認証済み情報を返す。"""
    return StoreManagerAuthContext(
        store_manager_id=201,
        store_id=101,
        name="Store Manager 1",
        email="manager1@example.com",
        roll_id=1,
        is_active=True,
    )


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app = FastAPI()
    app.include_router(payment_router, prefix="/payment")
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")
    app.include_router(face_router, prefix="/face")
    app.dependency_overrides[authenticate_store_manager] = override_store_manager_auth

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_without_store_manager_auth_override() -> Generator[TestClient, None, None]:
    """店舗管理者JWT認証を実際に実行するテストクライアント。"""
    app = FastAPI()
    app.include_router(store_router, prefix="/store")

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client_with_db(
) -> Generator[TestClient, None, None]:
    """DB接続設定を使用する共通テストクライアントを返す。"""

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
            "store_manager_jwt_secret": "test-store-manager-jwt-secret-at-least-32-characters",
            "store_manager_jwt_expire_seconds": 3600,
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


@pytest.fixture()
def store_client_with_db(
    client_with_db: TestClient,
    insert_store_managers,
) -> TestClient:
    """店舗101の管理者JWTを設定したstore API用DBテストクライアントを返す。"""
    login_response = client_with_db.post(
        "/store/manager/login",
        json={
            "email": "manager1@example.com",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    client_with_db.headers.update(
        {"Authorization": f"Bearer {access_token}"}
    )
    return client_with_db


@pytest.fixture()
def store_client_with_db_without_wallet_manager(
    store_client_with_db: TestClient,
) -> TestClient:
    """ウォレット未登録店舗104の管理者JWTへ切り替えたクライアントを返す。"""
    login_response = store_client_with_db.post(
        "/store/manager/login",
        json={
            "email": "no-wallet-manager@example.com",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    store_client_with_db.headers.update(
        {"Authorization": f"Bearer {access_token}"}
    )
    return store_client_with_db


@pytest.fixture()
def store_client_with_db_for_wallet_create(
    client_with_db: TestClient,
    insert_store_managers,
) -> TestClient:
    """ウォレット登録テスト専用店舗105の管理者JWTを設定したクライアントを返す。"""
    login_response = client_with_db.post(
        "/store/manager/login",
        json={
            "email": "wallet-create-manager@example.com",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    client_with_db.headers.update(
        {"Authorization": f"Bearer {access_token}"}
    )
    return client_with_db
