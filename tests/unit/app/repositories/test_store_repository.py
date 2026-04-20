from sqlalchemy.orm import Session

import pytest

from app.models.mysql.nonce import Nonce
from app.models.mysql.store_nonce import StoreNonce
from app.repositories.store_repository import StoreRepository


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestDeleteStoreNonceByNonceId:
    def test_delete_store_nonce_by_nonce_id(
        self,
        session: Session,
    ) -> None:
        """存在する nonce_id を指定した場合、対象 StoreNonce の deleted_at が設定されること。"""
        repository = StoreRepository()
        target_nonce_id = 1

        before = (
            session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert before.deleted_at is None

        repository.delete_store_nonce_by_nonce_id(session, target_nonce_id)
        session.flush()
        session.expire_all()

        after = (
            session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert after.deleted_at is not None

    def test_delete_store_nonce_by_nonce_id_not_found(
        self,
        session: Session,
    ) -> None:
        """存在しない nonce_id を指定した場合、いずれの StoreNonce も更新されないこと。"""
        repository = StoreRepository()
        non_existent_nonce_id = 99999

        repository.delete_store_nonce_by_nonce_id(session, non_existent_nonce_id)
        session.flush()
        session.expire_all()

        updated = (
            session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .all()
        )
        assert len(updated) == 0
