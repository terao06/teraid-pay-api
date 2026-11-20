"""デバイスのMySQL永続化処理を提供する。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST

from app.models.mysql.device import Device


class DeviceRepository:
    """デバイスの登録・検索・更新・論理削除を提供するRepository。

    Returns:
        デバイス永続化処理を提供するRepository。
    """

    def create_device(
        self,
        mysql_session: Session,
        device: Device,
    ) -> Device:
        """デバイスをセッションへ追加し、IDを確定する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            device: 登録対象のデバイス。

        Returns:
            IDが付与されたデバイス。
        """
        mysql_session.add(device)
        mysql_session.flush()
        return device

    def _build_devices_query(
        self,
        mysql_session: Session,
        store_id: int,
        device_name: str | None = None,
        is_active: bool | None = None,
    ):
        """店舗と検索条件を適用した未削除デバイスのクエリを構築する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 検索対象の店舗ID。
            device_name: デバイス名の部分一致条件。
            is_active: 利用可能状態の完全一致条件。

        Returns:
            店舗、論理削除、任意の検索条件を適用したクエリ。
        """
        query = mysql_session.query(Device).filter(
            Device.store_id == store_id,
            Device.deleted_at.is_(None),
        )
        if device_name is not None and (normalized_name := device_name.strip()):
            escaped_name = (
                normalized_name.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            query = query.filter(
                Device.device_name.ilike(f"%{escaped_name}%", escape="\\")
            )
        if is_active is not None:
            query = query.filter(Device.is_active.is_(is_active))
        return query

    def count_devices(
        self,
        mysql_session: Session,
        store_id: int,
        device_name: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """条件に一致する未削除デバイスの件数を取得する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 検索対象の店舗ID。
            device_name: デバイス名の部分一致条件。
            is_active: 利用可能状態の完全一致条件。

        Returns:
            条件に一致するデバイスの件数。
        """
        return self._build_devices_query(
            mysql_session=mysql_session,
            store_id=store_id,
            device_name=device_name,
            is_active=is_active,
        ).count()

    def get_devices(
        self,
        mysql_session: Session,
        store_id: int,
        device_name: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Device]:
        """条件に一致する未削除デバイスを登録日時の降順で取得する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 検索対象の店舗ID。
            device_name: デバイス名の部分一致条件。
            is_active: 利用可能状態の完全一致条件。
            offset: 読み飛ばす件数。
            limit: 最大取得件数。

        Returns:
            登録日時とデバイスIDの降順で並べたデバイス一覧。
        """
        return (
            self._build_devices_query(
                mysql_session=mysql_session,
                store_id=store_id,
                device_name=device_name,
                is_active=is_active,
            )
            .order_by(Device.created_at.desc(), Device.device_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_device(
        self,
        mysql_session: Session,
        store_id: int,
        device_id: int,
        lock_for_update: bool = False,
    ) -> Device | None:
        """店舗に属する未削除デバイスをIDで取得する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            store_id: 認証済み管理者の店舗ID。
            device_id: 取得対象のデバイスID。
            lock_for_update: 取得行を排他ロックする場合はTrue。

        Returns:
            条件に一致するデバイス。存在しない場合はNone。
        """
        query = (
            mysql_session.query(Device)
            .filter(
                Device.device_id == device_id,
                Device.store_id == store_id,
                Device.deleted_at.is_(None),
            )
        )
        if lock_for_update:
            query = query.with_for_update()
        return query.one_or_none()

    def get_device_by_activation_code_hash_for_update(
        self,
        mysql_session: Session,
        activation_code_hash: str,
    ) -> Device | None:
        """有効化コードのハッシュに一致する未削除端末を排他ロックして取得する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            activation_code_hash: 入力コードのSHA-256ハッシュ。

        Returns:
            一致する端末。存在しない場合はNone。
        """
        return (
            mysql_session.query(Device)
            .filter(
                Device.activation_code_hash == activation_code_hash,
                Device.deleted_at.is_(None),
            )
            .with_for_update()
            .one_or_none()
        )

    def get_device_by_uuid_for_update(
        self,
        mysql_session: Session,
        device_uuid: str,
    ) -> Device | None:
        """端末UUIDに一致する未削除端末を排他ロックして取得する。

        Args:
            mysql_session: トランザクション中のMySQLセッション。
            device_uuid: 取得対象の端末UUID。

        Returns:
            一致する端末。存在しない場合はNone。
        """
        return (
            mysql_session.query(Device)
            .filter(
                Device.device_uuid == device_uuid,
                Device.deleted_at.is_(None),
            )
            .with_for_update()
            .one_or_none()
        )

    def save_device(
        self,
        mysql_session: Session,
        device: Device,
    ) -> Device:
        """変更したデバイスをセッションへ保存する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            device: 保存対象のデバイス。

        Returns:
            保存したデバイス。
        """
        mysql_session.add(device)
        mysql_session.flush()
        return device

    def soft_delete_device(self, mysql_session: Session, device: Device) -> None:
        """デバイスへ削除日時を設定してセッションへ保存する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            device: 排他ロックして取得した削除対象デバイス。

        Returns:
            なし。
        """
        device.deleted_at = datetime.now(JST)
        mysql_session.add(device)
        mysql_session.flush()

