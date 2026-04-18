from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.mysql.base_model import Base
from tests.unit.test_data.mysql.build_local_db import (
    build_database_url,
    import_mysql_models,
    insert_stores as load_stores,
    insert_store_wallet_nonces as load_store_wallet_nonces,
    insert_store_wallets as load_store_wallets,
)

@pytest.fixture(scope="module")
def engine():
    import_mysql_models()
    engine = create_engine(build_database_url(), echo=False, future=True)
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
def insert_store_wallet_nonces(engine) -> str:
    return load_store_wallet_nonces(engine)
