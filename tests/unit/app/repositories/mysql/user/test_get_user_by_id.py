import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.user_repository import UserRepository


@pytest.mark.usefixtures("insert_users")
class TestGetUserById:
    """get_user_by_id の単体テスト。"""

    @pytest.mark.parametrize(
        ("user_id", "expected_user_id"),
        [
            (101, 101),
            (102, 102),
            (103, None),
            (999, None),
        ],
    )
    def test_get_user_by_id(
        self,
        mysql_session: Session,
        user_id: int,
        expected_user_id: int | None,
    ) -> None:
        """ユーザー ID からユーザー情報を取得し、論理削除と未存在は None を返すことを確認する。"""
        repository = UserRepository()

        result = repository.get_user_by_id(mysql_session, user_id)

        if expected_user_id is None:
            assert result is None
            return

        assert result is not None
        assert result.user_id == expected_user_id
