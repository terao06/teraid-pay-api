from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.mysql.store import Store
from app.models.mysql.wallet import Wallet
from app.models.mysql.store_wallet import StoreWallet
from app.models.mysql.store_nonce import StoreNonce
from app.models.mysql.store_manager import StoreManager
from app.models.mysql.menu_category import MenuCategory
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.nonce import Nonce
from app.core.utils.datetime import JST


class StoreRepository:
    """店舗ウォレット情報を取得するリポジトリです。"""

    def _build_menu_items_query(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        menu_category_id: int | None = None,
        is_available: bool | None = None,
    ):
        query = (
            mysql_session.query(
                MenuItem,
                MenuCategory.name.label("menu_category_name"),
            )
            .outerjoin(
                MenuCategory,
                and_(
                    MenuItem.menu_category_id == MenuCategory.menu_category_id,
                    MenuCategory.store_id == store_id,
                    MenuCategory.deleted_at.is_(None),
                ),
            )
            .filter(
                MenuItem.store_id == store_id,
                MenuItem.deleted_at.is_(None),
            )
        )

        if name is not None:
            normalized_name = name.strip()
            if normalized_name:
                escaped_name = (
                    normalized_name
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                )
                query = query.filter(
                    MenuItem.name.ilike(f"%{escaped_name}%", escape="\\")
                )

        if menu_category_id is not None:
            query = query.filter(
                MenuItem.menu_category_id == menu_category_id
            )

        if is_available is not None:
            query = query.filter(MenuItem.is_available.is_(is_available))

        return query

    def get_store_wallet_link(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_id: int,
    ) -> StoreWallet | None:
        """店舗IDとウォレットIDに一致する未削除の紐づけを取得する。"""
        return (
            mysql_session.query(StoreWallet)
            .filter(
                StoreWallet.store_id == store_id,
                StoreWallet.wallet_id == wallet_id,
                StoreWallet.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def get_store_manager_by_id(
        self,
        mysql_session: Session,
        store_manager_id: int,
    ) -> StoreManager | None:
        """店舗管理者IDに一致する未削除の管理者を取得する。"""
        return (
            mysql_session.query(StoreManager)
            .join(Store, StoreManager.store_id == Store.store_id)
            .filter(
                StoreManager.store_manager_id == store_manager_id,
                StoreManager.deleted_at.is_(None),
                Store.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def get_store_manager_by_email(
        self,
        mysql_session: Session,
        email: str,
    ) -> StoreManager | None:
        """有効な店舗に所属する店舗管理者をメールアドレスで取得する。"""
        return (
            mysql_session.query(StoreManager)
            .join(Store, StoreManager.store_id == Store.store_id)
            .filter(
                StoreManager.email == email,
                StoreManager.deleted_at.is_(None),
                Store.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def get_active_menu_categories(
        self,
        mysql_session: Session,
        store_id: int,
    ) -> list[MenuCategory]:
        """店舗に紐づく有効かつ未削除のメニューカテゴリーを取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            表示順で並べたメニューカテゴリー。存在しない場合は空のリスト。
        """
        return (
            mysql_session.query(MenuCategory)
            .filter(
                MenuCategory.store_id == store_id,
                MenuCategory.is_active.is_(True),
                MenuCategory.deleted_at.is_(None),
            )
            .order_by(
                MenuCategory.display_order.asc(),
                MenuCategory.menu_category_id.asc(),
            )
            .all()
        )

    def get_active_menu_category(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
    ) -> MenuCategory | None:
        """店舗に紐づく有効かつ未削除のメニューカテゴリーをIDで取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            menu_category_id: 対象カテゴリーの ID。

        Returns:
            条件に一致するメニューカテゴリー。存在しない場合は None。
        """
        return (
            mysql_session.query(MenuCategory)
            .filter(
                MenuCategory.menu_category_id == menu_category_id,
                MenuCategory.store_id == store_id,
                MenuCategory.is_active.is_(True),
                MenuCategory.deleted_at.is_(None),
            )
            .one_or_none()
        )

    def get_menu_items(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        menu_category_id: int | None = None,
        is_available: bool | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[tuple[MenuItem, str | None]]:
        """店舗に紐づく未削除のメニュー商品とカテゴリー名を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            表示順で並べたメニュー商品とカテゴリー名。存在しない場合は空のリスト。
        """
        query = self._build_menu_items_query(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            menu_category_id=menu_category_id,
            is_available=is_available,
        )
        query = query.order_by(
            MenuItem.display_order.asc(),
            MenuItem.menu_item_id.asc(),
        ).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def count_menu_items(
        self,
        mysql_session: Session,
        store_id: int,
        name: str | None = None,
        menu_category_id: int | None = None,
        is_available: bool | None = None,
    ) -> int:
        """検索条件に一致する未削除メニュー商品の件数を取得する。"""
        return self._build_menu_items_query(
            mysql_session=mysql_session,
            store_id=store_id,
            name=name,
            menu_category_id=menu_category_id,
            is_available=is_available,
        ).count()

    def create_menu_item(
        self,
        mysql_session: Session,
        menu_item: MenuItem,
    ) -> MenuItem:
        """メニュー商品を保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            menu_item: 保存するメニュー商品。

        Returns:
            IDが付与されたメニュー商品。
        """
        mysql_session.add(menu_item)
        mysql_session.flush()
        return menu_item

    def create_menu_option_group(
        self,
        mysql_session: Session,
        menu_option_group: MenuOptionGroup,
    ) -> MenuOptionGroup:
        """メニューオプショングループを保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            menu_option_group: 保存するメニューオプショングループ。

        Returns:
            IDが付与されたメニューオプショングループ。
        """
        mysql_session.add(menu_option_group)
        mysql_session.flush()
        return menu_option_group

    def create_menu_option(
        self,
        mysql_session: Session,
        menu_option: MenuOption,
    ) -> MenuOption:
        """メニューオプションを保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            menu_option: 保存するメニューオプション。

        Returns:
            IDが付与されたメニューオプション。
        """
        mysql_session.add(menu_option)
        mysql_session.flush()
        return menu_option

    def get_store_wallet(self, mysql_session: Session, store_id: int) -> Wallet | None:
        """店舗に紐づくウォレットを取得します。
        Args:
            mysql_session: SQLAlchemy のセッションです。
            store_id: 絞り込み対象の店舗 ID です。

        Returns:
            Wallet: ウォレット情報。
        """
        return mysql_session.query(Wallet
        ).join(
            StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id
        ).join(
            Store, StoreWallet.store_id == Store.store_id
        ).where(
            Store.store_id == store_id,
            Store.deleted_at.is_(None),
            StoreWallet.deleted_at.is_(None),
            Wallet.deleted_at.is_(None)
        ).first()

    def get_store_by_id(self, mysql_session: Session, store_id: int) -> Store | None:
        """店舗 ID から店舗情報を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。

        Returns:
            取得した店舗情報。存在しない場合は `None`。
        """
        return mysql_session.query(Store).where(
            Store.store_id == store_id,
            Store.deleted_at.is_(None)
        ).one_or_none()

    def create_store_nonce(self, mysql_session: Session, store_nonce: StoreNonce) -> None:
        """店舗 nonce を保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_nonce: 保存する店舗 nonce エンティティ。

        Returns:
            なし。
        """
        mysql_session.add(store_nonce)
    
    def get_wallet_by_store_id(
        self,
        mysql_session: Session,
        store_id: int,
        chain_type: str,
        network_name: str,
        chain_id: int,
    ) -> Wallet | None:
        """ウォレットアドレスに紐づく店舗ウォレットを取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 店舗ID
            chain_type: チェーン種別。
            network_name: ネットワーク名。

        Returns:
            該当する店舗ウォレット。存在しない場合は `None`。
        """
        return (
            mysql_session.query(Wallet)
            .join(StoreWallet, Wallet.wallet_id == StoreWallet.wallet_id)
            .where(StoreWallet.store_id == store_id)
            .where(StoreWallet.deleted_at.is_(None))
            .where(Wallet.chain_type == chain_type)
            .where(Wallet.network_name == network_name)
            .where(Wallet.chain_id == chain_id)
            .where(Wallet.deleted_at.is_(None))
        ).first()

    def get_latest_available_nonce(
        self,
        mysql_session: Session,
        store_id: int,
        wallet_address: str,
        chain_type: str,
        network_name: str,
        expires_at: datetime) -> Nonce | None:
        """利用可能な最新の nonce を取得する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_id: 対象店舗の ID。
            wallet_address: 対象ウォレットアドレス。
            chain_type: チェーン種別。
            network_name: ネットワーク名。
            expires_at: 有効期限の下限日時。

        Returns:
            利用可能な最新 nonce。存在しない場合は `None`。
        """

        return (
            mysql_session.query(Nonce)
            .join(StoreNonce, StoreNonce.nonce_id == Nonce.nonce_id)
            .where(StoreNonce.store_id == store_id)
            .where(StoreNonce.deleted_at.is_(None))
            .where(Nonce.wallet_address == wallet_address)
            .where(Nonce.chain_type == chain_type)
            .where(Nonce.network_name == network_name)
            .where(Nonce.used_at.is_(None))
            .where(Nonce.expires_at >= expires_at)
            .order_by(StoreNonce.store_nonce_id.desc())
        ).first()

    def create_store_wallet(self, mysql_session: Session, store_wallet: StoreWallet) -> None:
        """店舗ウォレットを保存対象としてセッションへ追加する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            store_wallet: 保存する店舗ウォレット。

        Returns:
            store_wallet: idを付与したwallet情報
        """
        mysql_session.add(store_wallet)
        mysql_session.flush()
        return store_wallet

    def delete_store_nonce_by_nonce_id(self, mysql_session: Session, nonce_id: int) -> None:
        """対象のnonceを論理削除する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            nonce_id: nonce id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            mysql_session.query(StoreNonce)
            .where(StoreNonce.nonce_id == nonce_id)
            .update({StoreNonce.deleted_at: now, StoreNonce.updated_at: now})
        )

    def delete_store_wallet_by_wallet_id(self, mysql_session: Session, wallet_id: int) -> None:
        """wallet_idを指定し対象の店舗ウォレット紐づけを論理削除する。

        Args:
            mysql_session: SQLAlchemy のセッション。
            wallet_id: wallet_id

        Returns:
            なし。
        
        """
        now = datetime.now(JST)
        (
            mysql_session.query(StoreWallet)
            .where(StoreWallet.wallet_id == wallet_id)
            .update({StoreWallet.deleted_at: now, StoreWallet.updated_at: now})
        )
