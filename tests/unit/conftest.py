from collections.abc import Generator

import pytest
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.mysql.base_model import Base
from tests.unit.test_data.mysql.build_local_db import (
    build_database_url,
    import_mysql_models,
    insert_nonces as load_nonces,
    insert_store_nonces as load_store_nonces,
    insert_stores as load_stores,
    insert_user_nonces as load_user_nonces,
    insert_users as load_users,
    insert_user_wallets as load_user_wallets,
    insert_wallets as load_wallets,
    insert_store_wallets as load_store_wallets,
)


@pytest.fixture(scope="module")
def engine():
    import_mysql_models()
    engine = create_engine(build_database_url(), echo=False, future=True)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        connection.execute(text("DROP TABLE IF EXISTS store_wallet_nonces"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture()
def insert_stores(engine) -> str:
    return load_stores(engine)


@pytest.fixture()
def insert_store_wallets(engine) -> str:
    return load_store_wallets(engine)


@pytest.fixture()
def insert_wallets(engine) -> str:
    return load_wallets(engine)


@pytest.fixture()
def insert_users(engine) -> str:
    return load_users(engine)


@pytest.fixture()
def insert_user_wallets(engine) -> str:
    return load_user_wallets(engine)


@pytest.fixture()
def insert_nonces(engine) -> str:
    return load_nonces(engine)


@pytest.fixture()
def insert_user_nonces(engine) -> str:
    return load_user_nonces(engine)


@pytest.fixture()
def insert_store_nonces(engine) -> str:
    return load_store_nonces(engine)
