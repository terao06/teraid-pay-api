import pytest
from sqlalchemy.orm import Session

from app.models.mysql.store_nonce import StoreNonce
from app.repositories.mysql.store_nonce_repository import StoreNonceRepository


@pytest.mark.usefixtures("insert_stores", "insert_nonces", "insert_store_nonces")
class TestDeleteStoreNonceByNonceId:
    """delete_store_nonce_by_nonce_id の動作を検証する。"""

    def test_delete_store_nonce_by_nonce_id(
        self,
        mysql_session: Session,
    ) -> None:
        """存在する nonce_id を指定した場合、対象 StoreNonce の deleted_at が設定されること。"""
        repository = StoreNonceRepository()
        target_nonce_id = 8

        before = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert before.deleted_at is None
        before_updated_at = before.updated_at

        repository.delete_store_nonce_by_nonce_id(mysql_session, target_nonce_id)
        mysql_session.flush()
        mysql_session.expire_all()

        after = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.nonce_id == target_nonce_id)
            .one()
        )
        assert after.deleted_at is not None
        assert after.updated_at is not None
        assert after.updated_at > before_updated_at

    def test_delete_store_nonce_by_nonce_id_not_found(
        self,
        mysql_session: Session,
    ) -> None:
        """存在しない nonce_id を指定した場合、いずれの StoreNonce も更新されないこと。"""
        repository = StoreNonceRepository()
        non_existent_nonce_id = 99999
        before_count = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .count()
        )

        repository.delete_store_nonce_by_nonce_id(mysql_session, non_existent_nonce_id)
        mysql_session.flush()
        mysql_session.expire_all()

        updated = (
            mysql_session.query(StoreNonce)
            .filter(StoreNonce.deleted_at.isnot(None))
            .all()
        )
        assert len(updated) == before_count
