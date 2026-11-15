"""店舗メニューとオプションを操作するRepository。"""

from sqlalchemy import and_
from sqlalchemy.orm import Session
from app.models.mysql.menu_category import MenuCategory
from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.repositories.mysql.store_menu_category_repository import StoreMenuCategoryRepository


class StoreMenuRepository(StoreMenuCategoryRepository):
    """店舗単位のメニュー検索とメニュー構成要素の登録処理を提供する。"""

    def _build_menu_items_query(self, mysql_session: Session, store_id: int, name: str | None = None,
                     menu_category_id: int | None = None, is_available: bool | None = None):
        """メニュー検索と件数取得で共有する絞り込みクエリを構築する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: メニュー名の部分一致条件。
            menu_category_id: カテゴリーIDの完全一致条件。
            is_available: 販売可能状態の完全一致条件。

        Returns:
            店舗、論理削除、任意の検索条件を適用したクエリ。
        """
        query = (mysql_session.query(MenuItem, MenuCategory.name.label("menu_category_name"))
                 .outerjoin(MenuCategory, and_(MenuItem.menu_category_id == MenuCategory.menu_category_id,
                                               MenuCategory.store_id == store_id, MenuCategory.deleted_at.is_(None)))
                 .filter(MenuItem.store_id == store_id, MenuItem.deleted_at.is_(None)))
        if name is not None and (normalized_name := name.strip()):
            escaped_name = normalized_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(MenuItem.name.ilike(f"%{escaped_name}%", escape="\\"))
        if menu_category_id is not None:
            query = query.filter(MenuItem.menu_category_id == menu_category_id)
        if is_available is not None:
            query = query.filter(MenuItem.is_available.is_(is_available))
        return query

    def get_menu_items(self, mysql_session: Session, store_id: int, name: str | None = None,
                       menu_category_id: int | None = None, is_available: bool | None = None,
                       offset: int = 0, limit: int | None = None) -> list[tuple[MenuItem, str | None]]:
        """条件に一致するメニューとカテゴリー名を表示順で取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: メニュー名の部分一致条件。
            menu_category_id: カテゴリーIDの完全一致条件。
            is_available: 販売可能状態の完全一致条件。
            offset: 読み飛ばす件数。
            limit: 最大取得件数。Noneの場合は制限しない。

        Returns:
            メニューとカテゴリー名のタプルのリスト。
        """
        query = self._build_menu_items_query(mysql_session, store_id, name, menu_category_id, is_available).order_by(
            MenuItem.display_order.asc(), MenuItem.menu_item_id.asc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def count_menu_items(self, mysql_session: Session, store_id: int, name: str | None = None,
                         menu_category_id: int | None = None, is_available: bool | None = None) -> int:
        """条件に一致するメニュー数を取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: メニュー名の部分一致条件。
            menu_category_id: カテゴリーIDの完全一致条件。
            is_available: 販売可能状態の完全一致条件。

        Returns:
            条件に一致するメニュー数。
        """
        return self._build_menu_items_query(mysql_session, store_id, name, menu_category_id, is_available).count()

    def get_menu_detail(
        self,
        mysql_session: Session,
        store_id: int,
        menu_item_id: int,
    ) -> list[
        tuple[
            MenuItem,
            str | None,
            MenuOptionGroup | None,
            MenuOption | None,
        ]
    ]:
        """店舗に属するメニュー商品と関連オプションを取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 認証済み管理者の店舗ID。
            menu_item_id: 取得対象のメニュー商品ID。

        Returns:
            商品、カテゴリー名、オプショングループ、オプションの行一覧。
            商品が存在しない場合は空の一覧。
        """
        return (
            mysql_session.query(
                MenuItem,
                MenuCategory.name.label("menu_category_name"),
                MenuOptionGroup,
                MenuOption,
            )
            .outerjoin(
                MenuCategory,
                and_(
                    MenuItem.menu_category_id == MenuCategory.menu_category_id,
                    MenuCategory.store_id == store_id,
                    MenuCategory.deleted_at.is_(None),
                ),
            )
            .outerjoin(
                MenuOptionGroup,
                and_(
                    MenuOptionGroup.menu_item_id == MenuItem.menu_item_id,
                    MenuOptionGroup.deleted_at.is_(None),
                ),
            )
            .outerjoin(
                MenuOption,
                and_(
                    MenuOption.menu_option_group_id
                    == MenuOptionGroup.menu_option_group_id,
                    MenuOption.deleted_at.is_(None),
                ),
            )
            .filter(
                MenuItem.menu_item_id == menu_item_id,
                MenuItem.store_id == store_id,
                MenuItem.deleted_at.is_(None),
            )
            .order_by(
                MenuOptionGroup.display_order.asc(),
                MenuOptionGroup.menu_option_group_id.asc(),
                MenuOption.display_order.asc(),
                MenuOption.menu_option_id.asc(),
            )
            .all()
        )

    def get_menu_item_for_update(
        self,
        mysql_session: Session,
        store_id: int,
        menu_item_id: int,
    ) -> MenuItem | None:
        """店舗に属する未削除の商品を排他ロックして取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 認証済み管理者の店舗ID。
            menu_item_id: 更新対象のメニュー商品ID。

        Returns:
            ロックしたメニュー商品。該当商品がない場合はNone。
        """
        return (
            mysql_session.query(MenuItem)
            .filter(
                MenuItem.menu_item_id == menu_item_id,
                MenuItem.store_id == store_id,
                MenuItem.deleted_at.is_(None),
            )
            .with_for_update()
            .one_or_none()
        )

    def update_menu_item(
        self,
        mysql_session: Session,
        menu_item: MenuItem,
    ) -> MenuItem:
        """メニュー商品を更新してセッションへ反映する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_item: 更新対象のメニュー商品。

        Returns:
            更新済みのメニュー商品。
        """
        mysql_session.add(menu_item)
        mysql_session.flush()
        return menu_item

    def create_menu_item(self, mysql_session: Session, menu_item: MenuItem) -> MenuItem:
        """メニューをセッションへ追加してIDを確定する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_item: 登録対象のメニュー。

        Returns:
            IDが付与されたメニュー。
        """
        mysql_session.add(menu_item); mysql_session.flush(); return menu_item

    def create_menu_option_group(self, mysql_session: Session,
                                 menu_option_group: MenuOptionGroup) -> MenuOptionGroup:
        """メニューオプショングループを追加してIDを確定する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_option_group: 登録対象のオプショングループ。

        Returns:
            IDが付与されたオプショングループ。
        """
        mysql_session.add(menu_option_group); mysql_session.flush(); return menu_option_group

    def create_menu_option(self, mysql_session: Session, menu_option: MenuOption) -> MenuOption:
        """メニューオプションを追加してIDを確定する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_option: 登録対象のオプション。

        Returns:
            IDが付与されたオプション。
        """
        mysql_session.add(menu_option); mysql_session.flush(); return menu_option
