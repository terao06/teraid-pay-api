import pytest
from sqlalchemy.orm import Session

from app.models.mysql.user_nonce import UserNonce
from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users", "insert_nonces")
class TestCreateUserNonce:
    """create_user_nonce の単体テスト。"""

    def test_create_user_nonce(
        self,
        mysql_session: Session,
    ) -> None:
        """user_nonce を追加し、flush 後に永続化内容を取得できることを検証する。"""
        repository = UserRepository()
        user_nonce = UserNonce(
            user_id=101,
            nonce_id=1,
        )

        repository.create_user_nonce(mysql_session, user_nonce)
        mysql_session.flush()
        mysql_session.expire_all()

        saved_user_nonce = (
            mysql_session.query(UserNonce)
            .filter(UserNonce.user_nonce_id == user_nonce.user_nonce_id)
            .one()
        )

        assert saved_user_nonce.user_nonce_id is not None
        assert saved_user_nonce.user_id == 101
        assert saved_user_nonce.nonce_id == 1
        assert saved_user_nonce.created_at is not None
        assert saved_user_nonce.updated_at is not None
        assert saved_user_nonce.deleted_at is None
