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
    insert_nonces as load_nonces,
    insert_payment_requests as load_payment_requests,
    insert_store_nonces as load_store_nonces,
    insert_stores as load_stores,
    insert_user_nonces as load_user_nonces,
    insert_users as load_users,
    insert_user_wallets as load_user_wallets,
    insert_wallets as load_wallets,
    insert_store_wallets as load_store_wallets,
)
from tests.unit.test_data.postgres.build_local_db import (
    build_database_url as build_postgres_database_url,
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
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        connection.execute(text("DROP TABLE IF EXISTS store_wallet_nonces"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    MySQLBase.metadata.drop_all(bind=engine)
    MySQLBase.metadata.create_all(bind=engine)
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
    engine = create_engine(build_postgres_database_url(), echo=False, future=True)
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
    return load_stores(mysql_engine)


@pytest.fixture()
def insert_store_wallets(mysql_engine) -> str:
    return load_store_wallets(mysql_engine)


@pytest.fixture()
def insert_wallets(mysql_engine) -> str:
    return load_wallets(mysql_engine)


@pytest.fixture()
def insert_users(mysql_engine) -> str:
    return load_users(mysql_engine)


@pytest.fixture()
def insert_user_wallets(mysql_engine) -> str:
    return load_user_wallets(mysql_engine)


@pytest.fixture()
def insert_nonces(mysql_engine) -> str:
    return load_nonces(mysql_engine)


@pytest.fixture()
def insert_user_nonces(mysql_engine) -> str:
    return load_user_nonces(mysql_engine)


@pytest.fixture()
def insert_store_nonces(mysql_engine) -> str:
    return load_store_nonces(mysql_engine)


@pytest.fixture()
def insert_payment_requests(mysql_engine) -> str:
    load_stores(mysql_engine)
    load_users(mysql_engine)
    return load_payment_requests(mysql_engine)


@pytest.fixture()
def insert_face_embeddings(postgres_engine) -> str:
    return load_face_embeddings(postgres_engine)
