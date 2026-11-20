"""端末UUIDによる排他ロック付き取得のRepositoryテスト。"""

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.mysql.device import Device
from app.repositories.mysql.device_repository import DeviceRepository


@pytest.mark.usefixtures("insert_device_access_token_data")
class TestGetDeviceByUuidForUpdate:
    """端末UUIDによる検索と排他ロックを検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("device_uuid", "expected_device_id"),
        [
            ("81005100-0000-4000-8000-000000000051", 810051),
            ("81005200-0000-4000-8000-000000000052", 810052),
            ("81005300-0000-4000-8000-000000000053", None),
            ("81005900-0000-4000-8000-000000000059", None),
        ],
    )
    def test_get_device_by_uuid_for_update(
        self,
        mysql_session: Session,
        device_uuid: str,
        expected_device_id: int | None,
    ) -> None:
        """UUIDに一致する未削除端末の取得と、削除済み・未登録端末の除外を確認する。

        Args:
            mysql_session: テスト用のMySQLセッション。
            device_uuid: 検索対象の端末UUID。
            expected_device_id: 取得される端末ID。対象外の場合はNone。

        Returns:
            なし。
        """
        result = DeviceRepository().get_device_by_uuid_for_update(
            mysql_session=mysql_session,
            device_uuid=device_uuid,
        )

        if expected_device_id is None:
            assert result is None
            return

        assert result is not None
        assert result.device_id == expected_device_id

    def test_locks_device_until_transaction_ends(self, mysql_engine: Engine) -> None:
        """トランザクション終了まで別セッションが同じ端末をロックできないことを確認する。

        Args:
            mysql_engine: 独立した2つのセッションに接続を提供するMySQL Engine。

        Returns:
            なし。
        """
        device_id = 810051
        device_uuid = "81005100-0000-4000-8000-000000000051"
        competing_query = (
            select(Device.device_id)
            .where(Device.device_id == device_id)
            .with_for_update(nowait=True)
        )
        with Session(mysql_engine) as locking_session, Session(mysql_engine) as competing_session:
            device = DeviceRepository().get_device_by_uuid_for_update(
                mysql_session=locking_session,
                device_uuid=device_uuid,
            )
            assert device is not None
            assert device.device_id == device_id

            with pytest.raises(OperationalError) as exc_info:
                competing_session.scalar(competing_query)
            # MySQLのER_LOCK_NOWAIT。
            assert exc_info.value.orig.args[0] == 3572

            competing_session.rollback()
            locking_session.rollback()
            assert competing_session.scalar(competing_query) == device_id
