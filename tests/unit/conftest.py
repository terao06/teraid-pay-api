"""単体テストで共有するDB・AWS・テストデータfixtureを提供する。"""

import os
from collections.abc import Generator
from collections.abc import Callable

import boto3
import pytest
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.mysql.base_model import Base as MySQLBase
from app.models.postgres.base_model import Base as PostgresBase
from app.models.postgres.face_embedding import FaceEmbedding
from tests.unit.test_data.mysql.build_local_db import (
    build_database_url,
    import_mysql_models,
    insert_device_checkout_data as load_device_checkout_data,
    insert_face_checkout_payment_data as load_face_checkout_payment_data,
    insert_device_access_token_data as load_device_access_token_data,
    insert_device_activation_data as load_device_activation_data,
    insert_device_menu_categories as load_device_menu_categories,
    insert_device_menu_items as load_device_menu_items,
    insert_device_order_data as load_device_order_data,
    insert_device_order_history_data as load_device_order_history_data,
    insert_devices as load_devices,
    insert_menu_category_deletion_data as load_menu_category_deletion_data,
    insert_menu_deletion_data as load_menu_deletion_data,
    insert_menu_mutation_stores as load_menu_mutation_stores,
    insert_menu_option_groups_update as load_menu_option_groups_update,
    insert_sample_data as load_mysql_sample_data,
    insert_order_list_data as load_order_list_data,
    insert_visit_session_completion_data as load_visit_session_completion_data,
    insert_visit_session_data as load_visit_session_data,
)
from tests.unit.test_data.postgres.build_local_db import (
    build_database_url as build_postgres_database_url,
    ensure_database_exists as ensure_postgres_database_exists,
    import_postgres_models,
    insert_face_embeddings as load_face_embeddings,
)
from tests.unit.test_data.s3.build_s3 import (
    ENDPOINT_URL as S3_ENDPOINT_URL,
    upload_mock_s3,
)
from tests.unit.test_data.secret.insert_secret import (
    DEFAULT_ENDPOINT_URL as SECRETS_MANAGER_ENDPOINT_URL,
    DEFAULT_REGION as SECRETS_MANAGER_REGION_NAME,
    load_secret_string,
    upsert_secret,
)
from tests.unit.test_data.secret.insert_secret import DEFAULT_SECRET_FILE as SECRET_FILE_PATH
from tests.unit.test_data.ssm.build_ssm import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    ENDPOINT_URL,
    REGION_NAME,
    put_mock_ssm_parameters,
)


AWS_MOCK_ENV = {
    "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
    "AWS_REGION": REGION_NAME,
    "SSM_ENDPOINT": ENDPOINT_URL,
    "S3_ENDPOINT": S3_ENDPOINT_URL,
    "SECRETS_MANAGER_ENDPOINT": SECRETS_MANAGER_ENDPOINT_URL,
}


@pytest.fixture(scope="session")
def initialize_aws_env() -> bool:
    os.environ.update(AWS_MOCK_ENV)
    return True


@pytest.fixture(scope="session")
def initialize_ssm(initialize_aws_env: bool) -> dict[str, str]:
    """共通のSSM設定を一度だけ投入し、各テストの復元元を提供する。

    Args:
        initialize_aws_env: ローカルAWS接続情報を設定するフィクスチャー。

    Returns:
        SSMに投入した初期設定。
    """
    assert initialize_aws_env
    return put_mock_ssm_parameters()


@pytest.fixture(scope="session")
def put_ssm_parameter(initialize_aws_env: bool) -> Generator[Callable[[str, str], None], None, None]:
    """同じSSMクライアントでテスト用の設定項目を更新する。

    Args:
        initialize_aws_env: ローカルAWS接続情報を設定するフィクスチャー。

    Yields:
        設定名と値を受け取り、対象の設定だけを上書きする関数。
    """
    assert initialize_aws_env
    ssm_client = boto3.client(
        "ssm",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION_NAME,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    def _put_ssm_parameter(name: str, value: str) -> None:
        """SSMの指定項目を上書きする。"""
        ssm_client.put_parameter(Name=name, Value=value, Type="String", Overwrite=True)

    try:
        yield _put_ssm_parameter
    finally:
        ssm_client.close()


@pytest.fixture()
def use_local_s3_endpoint(
    initialize_ssm: dict[str, str],
    put_ssm_parameter: Callable[[str, str], None],
) -> Generator[None, None, None]:
    """テスト中だけS3の接続先をローカル向けに変更する。

    Args:
        initialize_ssm: セッション開始時に投入したSSM設定。
        put_ssm_parameter: 指定したSSM設定だけを上書きする関数。

    Yields:
        S3の接続先を切り替えたテスト環境。
    """
    put_ssm_parameter("s3_endpoint", S3_ENDPOINT_URL)
    try:
        yield
    finally:
        put_ssm_parameter("s3_endpoint", initialize_ssm["s3_endpoint"])


@pytest.fixture(scope="session")
def initialize_s3(initialize_aws_env: bool) -> None:
    upload_mock_s3()
    assert initialize_aws_env == True


@pytest.fixture(scope="session")
def initialize_secret(initialize_aws_env: bool) -> None:
    upsert_secret(
        secret_name="secret",
        secret_string=load_secret_string(SECRET_FILE_PATH.with_name("secret.sample.json")),
        endpoint_url=SECRETS_MANAGER_ENDPOINT_URL,
        region_name=SECRETS_MANAGER_REGION_NAME,
    )
    assert initialize_aws_env == True


@pytest.fixture(scope="session")
def mysql_engine() -> Generator[Engine, None, None]:
    """テストセッションの開始時にMySQLのテーブルとサンプルデータを初期化する。

    Yields:
        初期化済みのテスト用MySQL Engine。
    """
    import_mysql_models()
    engine = create_engine(build_database_url(), echo=False, future=True)
    try:
        MySQLBase.metadata.drop_all(bind=engine)
        MySQLBase.metadata.create_all(bind=engine)
        load_mysql_sample_data(engine)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def mysql_session(mysql_engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=mysql_engine, autoflush=False, autocommit=False, future=True)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture(scope="session")
def postgres_engine():
    import_postgres_models()
    database_url = build_postgres_database_url()
    ensure_postgres_database_exists(database_url)
    engine = create_engine(database_url, echo=False, future=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        PostgresBase.metadata.drop_all(bind=connection, tables=[FaceEmbedding.__table__])
        PostgresBase.metadata.create_all(bind=connection, tables=[FaceEmbedding.__table__])
    yield engine
    engine.dispose()


@pytest.fixture()
def postgres_session(postgres_engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False, future=True)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture()
def insert_stores(mysql_engine) -> str:
    return "stores.sql"


@pytest.fixture()
def insert_store_managers(mysql_engine, insert_stores) -> str:
    return "store_managers.sql"


@pytest.fixture()
def insert_menu_categories(mysql_engine, insert_stores) -> str:
    return "menu_categories.sql"


@pytest.fixture()
def insert_menu_items(mysql_engine, insert_menu_categories) -> str:
    return "menu_items.sql"


@pytest.fixture(scope="session")
def insert_menu_mutation_stores(mysql_engine: Engine) -> tuple[str, str]:
    return load_menu_mutation_stores(mysql_engine)


@pytest.fixture(scope="session")
def insert_menu_category_deletion_data(
    mysql_engine: Engine,
    insert_menu_mutation_stores: tuple[str, str],
) -> tuple[str, str]:
    return load_menu_category_deletion_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_menu_deletion_data(
    mysql_engine: Engine,
    insert_menu_mutation_stores: tuple[str, str],
) -> tuple[str, str, str]:
    return load_menu_deletion_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_menu_option_groups_update(
    mysql_engine: Engine,
    insert_menu_mutation_stores: tuple[str, str],
) -> str:
    return ", ".join(load_menu_option_groups_update(mysql_engine))


@pytest.fixture()
def insert_store_wallets(mysql_engine) -> str:
    return "store_wallets.sql"


@pytest.fixture(scope="session")
def insert_devices(mysql_engine: Engine) -> str:
    return load_devices(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_activation_data(mysql_engine: Engine) -> str:
    return load_device_activation_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_access_token_data(mysql_engine: Engine) -> str:
    return load_device_access_token_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_visit_session_data(mysql_engine: Engine) -> tuple[str, str, str]:
    return load_visit_session_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_visit_session_completion_data(mysql_engine: Engine) -> tuple[str, ...]:
    """来店セッション終了用の専用データをテストセッション中に一度投入する。

    Args:
        mysql_engine: 初期化済みのテスト用MySQL Engine。

    Returns:
        投入に使ったテーブル単位のSQLファイル名。
    """
    return load_visit_session_completion_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_menu_categories(
    mysql_engine: Engine,
    insert_visit_session_data: tuple[str, str, str],
) -> str:
    return load_device_menu_categories(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_menu_items(mysql_engine: Engine) -> tuple[str, ...]:
    """カテゴリー別メニュー取得専用の店舗とメニューを一度だけ投入する。

    Args:
        mysql_engine: 初期化済みのテスト用MySQL Engine。

    Returns:
        専用データを投入したSQLファイル名。
    """
    return load_device_menu_items(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_order_data(mysql_engine: Engine) -> tuple[str, ...]:
    """既存の注文一覧から分離した注文登録用データを準備する。

    Args:
        mysql_engine: 初期化済みのテスト用MySQL Engine。

    Returns:
        注文登録テストに使用するSQLファイル名。
    """
    return load_device_order_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_order_history_data(
    mysql_engine: Engine, insert_device_order_data: tuple[str, ...]
) -> tuple[str, ...]:
    """既存の店舗とカタログを使い、履歴取得専用のセッションと注文を投入する。

    Args:
        mysql_engine: 初期化済みのMySQL Engine。
        insert_device_order_data: 注文に必要な店舗とカタログのデータ。

    Returns:
        履歴取得専用データを投入したSQLファイル名。
    """
    return load_device_order_history_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_face_checkout_payment_data(mysql_engine: Engine) -> tuple[str, ...]:
    """顔認証決済開始のテスト専用の会計、注文、店舗と端末を投入する。

    Args:
        mysql_engine: 初期化済みのテスト用MySQL Engine。

    Returns:
        投入に使ったテーブル単位のSQLファイル名。
    """
    return load_face_checkout_payment_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_device_checkout_data(mysql_engine: Engine) -> tuple[str, ...]:
    """会計作成テスト専用のデータをテストセッション中に一度投入する。

    Args:
        mysql_engine: 初期化済みのテスト用MySQL Engine。

    Returns:
        会計作成用データを投入したSQLファイル名。
    """
    return load_device_checkout_data(mysql_engine)


@pytest.fixture(scope="session")
def insert_order_list_data(mysql_engine: Engine, insert_device_menu_items: tuple[str, ...]) -> tuple[str, ...]:
    return load_order_list_data(mysql_engine)


@pytest.fixture()
def insert_wallets(mysql_engine) -> str:
    return "wallets.sql"


@pytest.fixture()
def insert_users(mysql_engine) -> str:
    return "users.sql"


@pytest.fixture()
def insert_user_wallets(mysql_engine) -> str:
    return "user_wallets.sql"


@pytest.fixture()
def insert_nonces(mysql_engine) -> str:
    return "nonces.sql"


@pytest.fixture()
def insert_user_nonces(mysql_engine) -> str:
    return "user_nonces.sql"


@pytest.fixture()
def insert_store_nonces(mysql_engine) -> str:
    return "store_nonces.sql"


@pytest.fixture()
def insert_payment_requests(mysql_engine) -> str:
    return "payment_requests.sql"


@pytest.fixture()
def insert_face_embeddings(postgres_engine) -> str:
    return load_face_embeddings(postgres_engine)
