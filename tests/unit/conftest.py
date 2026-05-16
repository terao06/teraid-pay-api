from collections.abc import Generator

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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def postgres_engine():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    PostgresBase.metadata.create_all(bind=engine, tables=[FaceEmbedding.__table__])
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
