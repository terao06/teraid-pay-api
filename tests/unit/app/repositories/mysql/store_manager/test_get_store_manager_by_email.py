import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.store_manager_repository import StoreManagerRepository

@pytest.mark.usefixtures("insert_stores", "insert_store_managers")
class TestGetStoreManagerByEmail:
    """メールアドレスによる店舗管理者のJOIN検索を検証する。"""

    @pytest.mark.parametrize(
        ("email", "expected_store_manager_id"),
        [
            ("manager1@example.com", 201),
            ("inactive-manager@example.com", 202),
            ("deleted-manager@example.com", None),
            ("deleted-store-manager@example.com", None),
            ("missing-manager@example.com", None),
        ],
    )
    def test_get_store_manager_by_email(
        self,
        mysql_session: Session,
        email: str,
        expected_store_manager_id: int | None,
    ) -> None:
        """管理者と所属店舗が未削除の場合のみメールアドレスで取得できることを検証する。"""
        result = StoreManagerRepository().get_store_manager_by_email(
            mysql_session=mysql_session,
            email=email,
        )

        if expected_store_manager_id is None:
            assert result is None
            return

        assert result is not None
        assert result.store_manager_id == expected_store_manager_id
