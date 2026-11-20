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


def test_get_device_by_activation_code_hash_locks_only_matching_undeleted_device() -> None:
    """コードのハッシュと未削除条件で検索し、対象行を排他ロックする。"""
    mysql_session = Mock()
    activation_code_hash = "activation-code-hash"
    device = Device(activation_code_hash=activation_code_hash)
    query = mysql_session.query.return_value
    filtered_query = query.filter.return_value
    locked_query = filtered_query.with_for_update.return_value
    locked_query.one_or_none.return_value = device

    result = DeviceRepository().get_device_by_activation_code_hash_for_update(
        mysql_session=mysql_session,
        activation_code_hash=activation_code_hash,
    )

    assert result is device
    mysql_session.query.assert_called_once_with(Device)
    query.filter.assert_called_once()
    hash_condition, deletion_condition = query.filter.call_args.args
    assert hash_condition.compare(Device.activation_code_hash == activation_code_hash)
    assert deletion_condition.compare(Device.deleted_at.is_(None))
    filtered_query.with_for_update.assert_called_once_with()
    locked_query.one_or_none.assert_called_once_with()


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

