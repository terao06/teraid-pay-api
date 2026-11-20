"""単体テストで共有するDB・AWS・テストデータfixtureを提供する。"""

import os
from collections.abc import Generator
from collections.abc import Callable

import boto3
import pytest
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.models.mysql.base_model import Base as MySQLBase
from app.models.postgres.base_model import Base as PostgresBase
from app.models.postgres.face_embedding import FaceEmbedding
from tests.unit.test_data.mysql.build_local_db import (
    build_database_url,
    import_mysql_models,
    insert_device_activation_data as load_device_activation_data,
    insert_devices as load_devices,
    insert_menu_category_deletion_data as load_menu_category_deletion_data,
    insert_menu_deletion_data as load_menu_deletion_data,
    insert_menu_option_groups as load_menu_option_groups,
    insert_menu_options as load_menu_options,
    insert_sample_data as load_mysql_sample_data,
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
def initialize_ssm(initialize_aws_env: bool) -> None:
    put_mock_ssm_parameters()
    assert initialize_aws_env == True


@pytest.fixture()
def put_ssm_parameter(initialize_aws_env: bool) -> Callable[[str, str], None]:
    def _put_ssm_parameter(name: str, value: str) -> None:
        ssm_client = boto3.client(
            "ssm",
            endpoint_url=ENDPOINT_URL,
            region_name=REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        ssm_client.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True,
        )

    assert initialize_aws_env == True
    return _put_ssm_parameter


@pytest.fixture()
def use_local_s3_endpoint(
    put_ssm_parameter: Callable[[str, str], None],
) -> Generator[None, None, None]:
    put_ssm_parameter("s3_endpoint", S3_ENDPOINT_URL)
    yield
    put_mock_ssm_parameters()


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
def mysql_engine():
    import_mysql_models()
    engine = create_engine(build_database_url(), echo=False, future=True)
    MySQLBase.metadata.drop_all(bind=engine)
    MySQLBase.metadata.create_all(bind=engine)
    load_mysql_sample_data(engine)
    yield engine
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


@pytest.fixture()
def insert_menu_category_deletion_data(
    mysql_engine,
    insert_menu_items,
) -> Generator[tuple[str, str], None, None]:
    """カテゴリー削除専用の行を投入し、テスト後に取り除く。

    Args:
        mysql_engine: テスト用MySQL Engine。
        insert_menu_items: 共有の店舗、カテゴリー、商品を準備するfixture。

    Returns:
        実行したSQLファイル名の組を生成するfixture。
    """
    try:
        yield load_menu_category_deletion_data(mysql_engine)
    finally:
        with mysql_engine.begin() as connection:
            connection.exec_driver_sql("DELETE FROM menu_items WHERE menu_item_id = 830001")
            connection.exec_driver_sql(
                "DELETE FROM menu_categories WHERE menu_category_id IN (830001, 830002, 830003, 830004)"
            )


@pytest.fixture()
def insert_menu_deletion_data(
    mysql_engine,
    insert_menu_items,
) -> Generator[tuple[str, str, str], None, None]:
    """メニュー削除専用の行を投入し、テスト後に専用行を取り除く。

    Args:
        mysql_engine: テスト用MySQL Engine。
        insert_menu_items: 店舗と商品を含む共有データの準備用fixture。

    Returns:
        実行したSQLファイル名をテストに渡すジェネレーター。
    """
    try:
        yield load_menu_deletion_data(mysql_engine)
    finally:
        with mysql_engine.begin() as connection:
            connection.exec_driver_sql(
                "DELETE FROM menu_options WHERE menu_option_id IN (840001, 840002, 840003)"
            )
            connection.exec_driver_sql(
                "DELETE FROM menu_option_groups WHERE menu_option_group_id IN (840001, 840002, 840003)"
            )
            connection.exec_driver_sql(
                "DELETE FROM menu_items WHERE menu_item_id IN (840001, 840002, 840003, 840004)"
            )


@pytest.fixture()
def insert_menu_option_groups_update(
    mysql_engine,
    mysql_session: Session,
    insert_menu_items,
) -> Generator[str, None, None]:
    """オプション構成更新専用データを投入し、テスト後に削除する。

    Args:
        mysql_engine: テスト用MySQL Engine。
        mysql_session: テストから参照されるSQLAlchemyセッション。
        insert_menu_items: メニュー商品データ投入済みを示すfixture。

    Yields:
        実行したSQLファイル名。
    """
    group_file_name = load_menu_option_groups(mysql_engine)
    option_file_name = load_menu_options(mysql_engine)
    yield f"{group_file_name}, {option_file_name}"
    mysql_session.rollback()
    mysql_session.expire_all()
    with mysql_engine.begin() as connection:
        connection.exec_driver_sql(
            "DELETE menu_options FROM menu_options "
            "INNER JOIN menu_option_groups "
            "ON menu_options.menu_option_group_id = "
            "menu_option_groups.menu_option_group_id "
            "WHERE menu_option_groups.menu_item_id = 24"
        )
        connection.exec_driver_sql(
            "DELETE FROM menu_option_groups WHERE menu_item_id = 24"
        )


@pytest.fixture()
def insert_store_wallets(mysql_engine) -> str:
    return "store_wallets.sql"


@pytest.fixture()
def insert_devices(mysql_engine) -> Generator[str, None, None]:
    """devicesテーブルのテスト行を投入し、テスト後に除去する。

    Args:
        mysql_engine: テスト用MySQL Engine。

    Yields:
        実行したSQLファイル名。
    """
    file_name = load_devices(mysql_engine)
    try:
        yield file_name
    finally:
        with mysql_engine.begin() as connection:
            connection.exec_driver_sql(
                "DELETE FROM devices WHERE device_id IN "
                "(810001, 810002, 810003, 810011, 810012, 810021, 810022, 810031)"
            )


@pytest.fixture()
def insert_device_activation_data(mysql_engine) -> Generator[str, None, None]:
    """初回有効化の専用データを投入し、テスト後に削除する。

    Args:
        mysql_engine: テスト用MySQL Engine。

    Yields:
        実行したSQLファイル名。
    """
    file_name = load_device_activation_data(mysql_engine)
    try:
        yield file_name
    finally:
        with mysql_engine.begin() as connection:
            connection.exec_driver_sql(
                "DELETE FROM devices WHERE device_id IN (810041, 810042, 810043)"
            )


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
