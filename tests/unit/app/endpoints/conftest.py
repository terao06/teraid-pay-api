"""APIテスト用のFastAPIクライアントと認証フィクスチャを提供する。"""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.core.aws.secret_manager import SecretManager
from app.dependencies.store_manager_auth import (
    StoreManagerAuthContext,
    authenticate_store_manager,
)
from app.endpoints.device import device_router
from app.endpoints.face import face_router
from app.endpoints.payment import payment_router
from app.endpoints.store import store_router
from app.endpoints.user import user_router
from app.middlewares.request_wrapper import handle_request_validation_error
from app.middlewares.transaction import get_mysql_db, get_postgres_db
from tests.unit.test_data.mysql.build_local_db import build_database_url
from tests.unit.test_data.postgres.build_local_db import build_database_url as build_postgres_database_url


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


def _create_endpoint_app() -> FastAPI:
    """Endpointテストで使うルーターと共通の入力エラー処理を登録する。"""
    app = FastAPI()
    app.include_router(payment_router, prefix="/payment")
    app.include_router(store_router, prefix="/store")
    app.include_router(user_router, prefix="/user")
    app.include_router(face_router, prefix="/face")
    app.include_router(device_router, prefix="/device")
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)
    return app


@pytest.fixture(scope="session")
def endpoint_app() -> FastAPI:
    """実際の認証を実行するEndpointテスト用アプリを一度だけ作る。

    Args:
        なし。

    Returns:
        ルーター登録済みのFastAPIアプリ。
    """
    return _create_endpoint_app()


@pytest.fixture(scope="session")
def endpoint_app_with_auth_override() -> FastAPI:
    """店舗管理者認証を上書きしたEndpointテスト用アプリを一度だけ作る。

    Args:
        なし。

    Returns:
        固定の店舗管理者情報を使うFastAPIアプリ。
    """
    app = _create_endpoint_app()
    app.dependency_overrides[authenticate_store_manager] = override_store_manager_auth
    return app


@pytest.fixture()
def client(endpoint_app_with_auth_override: FastAPI) -> Generator[TestClient, None, None]:
    """共有アプリに対し、認証上書き付きの独立したクライアントを提供する。

    Args:
        endpoint_app_with_auth_override: 店舗管理者認証を上書きした共有アプリ。

    Yields:
        テスト専用のヘッダーとCookieを持つクライアント。
    """
    with TestClient(endpoint_app_with_auth_override) as test_client:
        yield test_client


@pytest.fixture()
def client_without_store_manager_auth_override(endpoint_app: FastAPI) -> Generator[TestClient, None, None]:
    """店舗管理者JWT認証を実行する独立したクライアントを提供する。

    Args:
        endpoint_app: 実際の認証を実行する共有アプリ。

    Yields:
        テスト専用のヘッダーとCookieを持つクライアント。
    """
    with TestClient(endpoint_app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def endpoint_database_secrets(initialize_aws_env: bool) -> Generator[dict[str, str | int | None], None, None]:
    """EndpointのDB接続情報と接続プールの有効期間を管理する。

    Args:
        initialize_aws_env: ローカルAWS接続情報を設定するフィクスチャー。

    Yields:
        テスト用のDB接続情報と認証設定。
    """
    mysql_url = make_url(build_database_url())
    postgres_url = make_url(build_postgres_database_url())
    secrets: dict[str, str | int | None] = {
        "mysql_user": mysql_url.username,
        "mysql_password": mysql_url.password,
        "mysql_host": mysql_url.host,
        "mysql_port": mysql_url.port,
        "mysql_database": mysql_url.database,
        "postgres_database": postgres_url.database,
        "postgres_user": postgres_url.username,
        "postgres_password": postgres_url.password,
        "postgres_host": postgres_url.host,
        "postgres_port": postgres_url.port,
        "store_manager_jwt_secret": "test-store-manager-jwt-secret-at-least-32-characters",
        "store_manager_jwt_expire_seconds": 3600,
        "device_jwt_secret": "test-device-jwt-secret-at-least-32-characters",
        "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/hogehoge",
        "chain_1_jpyc_token_address": "0x2222222222222222222222222222222222222222",
        "chain_1_payment_processor_address": "0x3333333333333333333333333333333333333333",
        "chain_1_payment_operator_private_key": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "chain_11155111_jpyc_token_address": "0x4444444444444444444444444444444444444444",
        "chain_11155111_payment_processor_address": "0x5555555555555555555555555555555555555555",
        "chain_11155111_payment_operator_private_key": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }
    database_factories = (get_mysql_db, get_postgres_db)
    for get_database in database_factories:
        get_database.cache_clear()
    try:
        assert initialize_aws_env
        with patch.object(SecretManager, "get_secret", return_value=secrets):
            # 初回のDBリクエストが並行実行でも、MySQLのプールを一度だけ作る。
            get_mysql_db().initialize()
        yield secrets
    finally:
        for get_database in database_factories:
            try:
                if get_database.cache_info().currsize:
                    get_database().engine.dispose()
            finally:
                get_database.cache_clear()


@pytest.fixture()
def client_with_db(
    endpoint_app: FastAPI,
    endpoint_database_secrets: dict[str, str | int | None],
) -> Generator[TestClient, None, None]:
    """共有アプリと接続プールを使う実DBテスト用クライアントを提供する。

    Args:
        endpoint_app: 実際の認証を実行する共有アプリ。
        endpoint_database_secrets: 開発環境とは分離したテスト用の接続情報。

    Yields:
        テスト専用のヘッダーとCookieを持つ実DBクライアント。
    """
    with patch.object(SecretManager, "get_secret", return_value=endpoint_database_secrets):
        with TestClient(endpoint_app) as test_client:
            yield test_client


@pytest.fixture(scope="session")
def store_manager_tokens() -> dict[str, str]:
    """実ログインで発行したテスト用JWTを管理者メールアドレスごとに保持する。

    Args:
        なし。

    Returns:
        ログイン済みの管理者を記録する辞書。
    """
    return {}


@pytest.fixture()
def store_client_with_db(
    client_with_db: TestClient,
    insert_store_managers,
    store_manager_tokens: dict[str, str],
    request: pytest.FixtureRequest,
) -> TestClient:
    """店舗管理者のJWTを設定したDBテストクライアントを返す。

    Args:
        client_with_db: 実際のMySQLに接続するAPIクライアント。
        insert_store_managers: 店舗管理者のテストデータを準備するフィクスチャ。
        store_manager_tokens: テストセッション中に発行済みのJWT。
        request: 間接パラメータで管理者のメールアドレスを受け取る。省略時は店舗101の管理者を使う。

    Returns:
        指定された管理者のJWTをAuthorizationヘッダーに設定したクライアント。
    """
    email = getattr(request, "param", "manager1@example.com")
    if email not in store_manager_tokens:
        login_response = client_with_db.post(
            "/store/manager/login",
            json={
                "email": email,
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        store_manager_tokens[email] = login_response.json()["data"]["access_token"]
    access_token = store_manager_tokens[email]
    client_with_db.headers.update(
        {"Authorization": f"Bearer {access_token}"}
    )
    return client_with_db
