"""店舗メニューカテゴリーを操作するRepository。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.utils.datetime import JST
from app.models.mysql.menu_category import MenuCategory


class StoreMenuCategoryRepository:
    """店舗単位のメニューカテゴリーの検索、登録、更新、論理削除を提供する。"""

    def _build_menu_categories_query(self, mysql_session: Session, store_id: int, name: str | None = None, is_active: bool = True):
        """カテゴリー検索と件数取得で共有する絞り込みクエリを構築する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: カテゴリー名の部分一致条件。
            is_active: 有効状態の完全一致条件。

        Returns:
            店舗、論理削除、有効状態、名称条件を適用したクエリ。
        """
        query = mysql_session.query(MenuCategory).filter(
            MenuCategory.store_id == store_id, MenuCategory.deleted_at.is_(None), MenuCategory.is_active.is_(is_active)
        )
        if name is not None and (normalized_name := name.strip()):
            escaped_name = normalized_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(MenuCategory.name.ilike(f"%{escaped_name}%", escape="\\"))
        return query

    def get_menu_categories(self, mysql_session: Session, store_id: int, name: str | None = None,
                            is_active: bool = True, offset: int = 0, limit: int | None = None) -> list[MenuCategory]:
        """条件に一致するメニューカテゴリーを表示順で取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: カテゴリー名の部分一致条件。
            is_active: 有効状態の完全一致条件。
            offset: 読み飛ばす件数。
            limit: 最大取得件数。Noneの場合は制限しない。

        Returns:
            条件に一致するメニューカテゴリーのリスト。
        """
        query = self._build_menu_categories_query(mysql_session, store_id, name, is_active).order_by(
            MenuCategory.display_order.asc(), MenuCategory.menu_category_id.asc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def count_menu_categories(self, mysql_session: Session, store_id: int, name: str | None = None,
                              is_active: bool = True) -> int:
        """条件に一致するメニューカテゴリー数を取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            name: カテゴリー名の部分一致条件。
            is_active: 有効状態の完全一致条件。

        Returns:
            条件に一致するカテゴリー数。
        """
        return self._build_menu_categories_query(mysql_session, store_id, name, is_active).count()

    def get_active_menu_category(self, mysql_session: Session, store_id: int,
                                 menu_category_id: int) -> MenuCategory | None:
        """店舗に属する有効なメニューカテゴリーをIDで取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 対象店舗ID。
            menu_category_id: メニューカテゴリーID。

        Returns:
            有効なカテゴリー。該当するレコードがない場合はNone。
        """
        return mysql_session.query(MenuCategory).filter(
            MenuCategory.menu_category_id == menu_category_id, MenuCategory.store_id == store_id,
            MenuCategory.is_active.is_(True), MenuCategory.deleted_at.is_(None),
        ).one_or_none()

    def get_menu_category_detail(
        self,
        mysql_session: Session,
        store_id: int,
        menu_category_id: int,
        *,
        lock_for_update: bool = False,
    ) -> MenuCategory | None:
        """店舗に属する未削除のメニューカテゴリーをIDで取得する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            store_id: 取得対象の店舗ID。
            menu_category_id: 取得対象のメニューカテゴリーID。
            lock_for_update: 取得行を排他ロックする場合はTrue。

        Returns:
            条件に一致するカテゴリー。該当レコードがない場合はNone。
        """
        query = mysql_session.query(MenuCategory).filter(
            MenuCategory.menu_category_id == menu_category_id,
            MenuCategory.store_id == store_id,
            MenuCategory.deleted_at.is_(None),
        )
        if lock_for_update:
            query = query.with_for_update()
        return query.one_or_none()

    def update_menu_category(
        self,
        mysql_session: Session,
        menu_category: MenuCategory,
    ) -> MenuCategory:
        """メニューカテゴリーを更新してセッションへ反映する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_category: 更新対象のメニューカテゴリー。

        Returns:
            更新済みのメニューカテゴリー。
        """
        mysql_session.add(menu_category)
        mysql_session.flush()
        return menu_category

    def soft_delete_menu_category(
        self,
        mysql_session: Session,
        menu_category: MenuCategory,
    ) -> None:
        """排他ロック済みのカテゴリーに削除日時を設定してDBへ反映する。

        Args:
            mysql_session: SQLAlchemyのMySQLセッション。
            menu_category: 排他ロックして取得した削除対象のカテゴリー。

        Returns:
            なし。

        Raises:
            SQLAlchemyError: DBへの反映に失敗した場合。
        """
        menu_category.deleted_at = datetime.now(JST)
        mysql_session.add(menu_category)
        mysql_session.flush()

    def create_menu_category(self, mysql_session: Session, menu_category: MenuCategory) -> MenuCategory:
        """メニューカテゴリーをセッションへ追加してIDを確定する。

        Args:
            mysql_session: SQLAlchemyのセッション。
            menu_category: 登録対象のカテゴリー。

        Returns:
            IDが付与されたカテゴリー。
        """
        mysql_session.add(menu_category)
        mysql_session.flush()
        return menu_category
