"""UUIDで未削除端末を参照する処理をMySQLで検証する。"""

import pytest
from sqlalchemy.orm import Session

from app.repositories.mysql.device_repository import DeviceRepository


@pytest.mark.usefixtures("insert_device_access_token_data")
class TestGetDeviceByUuid:
    """端末UUIDによる検索範囲を検証する。

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
        ids=["active", "stopped", "deleted", "missing"],
    )
    def test_finds_only_nondeleted_device_by_uuid(self, mysql_session: Session, device_uuid, expected_device_id) -> None:
        """UUIDで未削除行を参照し、削除済みまたは未登録の行を除外する。

        Args:
            mysql_session: テスト用のMySQLセッション。
            device_uuid: 検索対象の端末UUID。
            expected_device_id: 期待する端末ID。該当なしの場合はNone。

        Returns:
            なし。
        """
        result = DeviceRepository().get_device_by_uuid(mysql_session=mysql_session, device_uuid=device_uuid)

        if expected_device_id is None:
            assert result is None
        else:
            assert result.device_id == expected_device_id
            assert result.store_id == 101
