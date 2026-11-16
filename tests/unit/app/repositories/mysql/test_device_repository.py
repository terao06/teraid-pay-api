"""デバイスRepositoryのテスト。"""

from unittest.mock import Mock

from app.models.mysql.device import Device
from app.repositories.mysql.device_repository import DeviceRepository


def test_create_device_adds_and_flushes_device() -> None:
    """デバイスをセッションへ追加してflushする。"""
    mysql_session = Mock()
    device = Device(store_id=101, device_name="レジ端末1", device_uuid="uuid")

    result = DeviceRepository().create_device(
        mysql_session=mysql_session,
        device=device,
    )

    assert result is device
    mysql_session.add.assert_called_once_with(device)
    mysql_session.flush.assert_called_once_with()


def test_save_device_adds_and_flushes_device() -> None:
    """変更したデバイスをセッションへ追加してflushする。"""
    mysql_session = Mock()
    device = Device(store_id=101, device_name="更新後", device_uuid="uuid")

    result = DeviceRepository().save_device(
        mysql_session=mysql_session,
        device=device,
    )

    assert result is device
    mysql_session.add.assert_called_once_with(device)
    mysql_session.flush.assert_called_once_with()

