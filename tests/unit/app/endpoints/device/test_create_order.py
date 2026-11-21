"""注文登録APIの入力、認証、永続化、並行再送を検証する。"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from sqlalchemy import event, select

from app.core.config.device_auth import DeviceAuthConfig
from app.core.exceptions.message import DEVICE_ORDER_CONFLICT_ERROR
from app.core.utils.device_auth import DeviceAuthUtil
from app.middlewares.transaction import get_mysql_db
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.menu_order_item import MenuOrderItem
from app.models.mysql.menu_order_item_option import MenuOrderItemOption
from app.repositories.mysql.device_order_repository import DeviceOrderRepository


PATH = "/device/visit-sessions/{visit_id}/orders"
DEVICE_UUID = "88100100-0000-4000-8000-000000881001"
OTHER_UUID = "86100200-0000-4000-8000-000000861002"
DISABLED_UUID = "88100200-0000-4000-8000-000000881002"
JWT_SECRET = "test-device-jwt-secret-at-least-32-characters"
ACTIVE_VISIT = 882001
POTATO = {"menu_item_id": 883002, "quantity": 1, "options": []}
BURGER = {
    "menu_item_id": 883001,
    "quantity": 2,
    "options": [
        {"menu_option_id": 885001, "option_quantity": 2},
        {"menu_option_id": 885002, "option_quantity": 1},
    ],
}


def _headers(key: str, device_uuid: str = DEVICE_UUID) -> dict[str, str]:
    """テスト用端末のBearer認証と注文キーのヘッダーを作る。"""
    token = DeviceAuthUtil.create_access_token(device_uuid, DeviceAuthConfig(JWT_SECRET, 300))
    return {"Authorization": f"Bearer {token}", "Idempotency-Key": key}


class TestCreateOrder:
    """端末の注文登録をHTTPから検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(("visit_id", "key", "body"), [
        ("0", "test-key", {"items": [POTATO]}),
        ("1.0", "test-key", {"items": [POTATO]}),
        ("9223372036854775808", "test-key", {"items": [POTATO]}),
        (ACTIVE_VISIT, None, {"items": [POTATO]}),
        (ACTIVE_VISIT, "  ", {"items": [POTATO]}),
        (ACTIVE_VISIT, "x" * 65, {"items": [POTATO]}),
        (ACTIVE_VISIT, "test-key", {"items": []}),
        (ACTIVE_VISIT, "test-key", {"items": [{**POTATO, "quantity": True}]}),
        (ACTIVE_VISIT, "test-key", {"items": [{**POTATO, "quantity": "1"}]}),
        (ACTIVE_VISIT, "test-key", {"items": [{**POTATO, "quantity": 4294967296}]}),
        (ACTIVE_VISIT, "test-key", {"items": [{**POTATO, "quantity": 0}]}),
        (ACTIVE_VISIT, "test-key", {"items": [{**POTATO, "options": [{"menu_option_id": 1, "option_quantity": 0}]}]}),
    ])
    def test_rejects_invalid_input_before_mysql(self, client, visit_id, key, body) -> None:
        """形式が不正な入力を422にし、入力値を応答に含めない。

        Args:
            client: HTTPクライアント。
            visit_id: 検証対象のパスID。
            key: 検証対象のキー。
            body: 検証対象のリクエスト本文。

        Returns:
            なし。
        """
        headers = {} if key is None else {"Idempotency-Key": key}
        with patch("app.middlewares.transaction.get_mysql_db") as mysql:
            response = client.post(PATH.format(visit_id=visit_id), headers=headers, json=body)
        assert response.status_code == 422
        assert all(set(error) == {"loc", "type", "msg"} for error in response.json()["detail"])
        mysql.assert_not_called()

    def test_requires_bearer_before_mysql(self, client) -> None:
        """BearerトークンがないときにDB接続前に401を返す。

        Args:
            client: HTTPクライアント。

        Returns:
            なし。
        """
        with patch("app.middlewares.transaction.get_mysql_db") as mysql:
            response = client.post(
                PATH.format(visit_id=ACTIVE_VISIT),
                headers={"Idempotency-Key": "missing-token"},
                json={"items": [POTATO]},
            )
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        mysql.assert_not_called()

    @pytest.mark.usefixtures("insert_device_order_data")
    def test_with_db_creates_and_replays_order(self, client_with_db, mysql_session) -> None:
        """新規と再送のSELECT数、および保存された価格と明細を確認する。

        Args:
            client_with_db: 端末認証とMySQLを使用するHTTPクライアント。
            mysql_session: 保存結果を別接続から検証するセッション。

        Returns:
            なし。
        """
        statements = []

        def record_select(conn, cursor, statement, parameters, context, executemany):
            """API接続が実行するSELECTだけを記録する。"""
            if statement.lstrip().startswith("SELECT"):
                statements.append(statement)

        url = PATH.format(visit_id=ACTIVE_VISIT)
        headers = _headers("order-create-replay")
        engine = get_mysql_db().engine
        event.listen(engine, "before_cursor_execute", record_select)
        try:
            created = client_with_db.post(url, headers=headers, json={"items": [BURGER, POTATO]})
            assert created.status_code == 201
            assert len(statements) == 4
            assert all("FOR UPDATE" in sql for sql in statements[-2:])
            statements.clear()
            reversed_burger = {**BURGER, "options": list(reversed(BURGER["options"]))}
            replay = client_with_db.post(url, headers=headers, json={"items": [POTATO, reversed_burger]})
            assert replay.status_code == 200
            assert len(statements) == 1
        finally:
            event.remove(engine, "before_cursor_execute", record_select)

        assert replay.json() == created.json()
        assert created.headers["Cache-Control"] == replay.headers["Cache-Control"] == "no-store"
        order_id = created.json()["menu_order_id"]
        assert created.json() == {"menu_order_id": order_id, "total_amount": "2022.750000", "token_symbol": "JPYC"}
        order = mysql_session.get(MenuOrder, order_id)
        assert (order.store_id, order.visit_session_id, order.status, order.user_id, order.served_at) == (
            113, ACTIVE_VISIT, OrderStatus.PENDING_PAYMENT.value, None, None,
        )
        lines = mysql_session.scalars(
            select(MenuOrderItem).where(MenuOrderItem.menu_order_id == order_id).order_by(MenuOrderItem.display_order)
        ).all()
        assert [(x.menu_item_id, x.quantity, x.unit_price, x.line_amount) for x in lines] == [
            (883001, 2, Decimal("650.25"), Decimal("1722.75")),
            (883002, 1, Decimal("300"), Decimal("300")),
        ]
        options = mysql_session.scalars(select(MenuOrderItemOption).where(
            MenuOrderItemOption.menu_order_item_id == lines[0].menu_order_item_id
        ).order_by(MenuOrderItemOption.display_order)).all()
        assert [(x.menu_option_id, x.option_quantity, x.additional_price) for x in options] == [
            (885001, 2, Decimal("100.5")), (885002, 1, Decimal("10.125")),
        ]

        extra = client_with_db.post(url, headers=_headers("order-extra"), json={"items": [POTATO]})
        assert extra.status_code == 201
        assert extra.json()["menu_order_id"] != order_id

    @pytest.mark.usefixtures("insert_device_order_data", "insert_device_menu_items")
    def test_with_db_rejects_idempotency_conflicts(self, client_with_db) -> None:
        """同じキーを違う内容や店舗で使うと既存注文の情報を含まず409を返す。

        Args:
            client_with_db: 端末認証とMySQLを使用するHTTPクライアント。

        Returns:
            なし。
        """
        url = PATH.format(visit_id=ACTIVE_VISIT)
        key = "order-global-conflict"
        created = client_with_db.post(url, headers=_headers(key), json={"items": [POTATO]})
        assert created.status_code == 201

        different_body = client_with_db.post(url, headers=_headers(key), json={"items": [BURGER]})
        different_store = client_with_db.post(
            PATH.format(visit_id=862002), headers=_headers(key, OTHER_UUID), json={"items": [POTATO]},
        )
        for response in (different_body, different_store):
            assert response.status_code == 409
            assert response.json() == {"detail": {"status": "error", "message": DEVICE_ORDER_CONFLICT_ERROR}}

    @pytest.mark.parametrize(("device_uuid", "visit_id", "status"), [
        (DISABLED_UUID, ACTIVE_VISIT, 401),
        (DEVICE_UUID, 882002, 404),
        (DEVICE_UUID, 862002, 404),
        (DEVICE_UUID, 999999999, 404),
    ])
    @pytest.mark.usefixtures("insert_device_order_data", "insert_device_menu_items")
    def test_with_db_rejects_unavailable_device_or_visit(self, client_with_db, device_uuid, visit_id, status) -> None:
        """端末の状態とセッションの所属・受付可否を判定する。

        Args:
            client_with_db: DBに接続するHTTPクライアント。
            device_uuid: 認証トークンの端末UUID。
            visit_id: 注文先の来店セッション。
            status: 期待するHTTPステータス。

        Returns:
            なし。
        """
        response = client_with_db.post(
            PATH.format(visit_id=visit_id), headers=_headers("order-unavailable", device_uuid), json={"items": [POTATO]},
        )
        assert response.status_code == status
        if status == 401:
            assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize("items", [
        [{**POTATO, "menu_item_id": 863014}],
        [{**POTATO, "menu_item_id": 883003}],
        [{**BURGER, "options": []}],
        [{**BURGER, "options": [{"menu_option_id": 885001, "option_quantity": 4}]}],
        [{**BURGER, "options": [{"menu_option_id": 885003, "option_quantity": 1}]}],
        [{**POTATO, "options": BURGER["options"]}],
        [POTATO, {**POTATO, "menu_item_id": 883004}],
    ])
    @pytest.mark.usefixtures("insert_device_order_data", "insert_device_menu_items")
    def test_with_db_rejects_invalid_catalog_selections(self, client_with_db, mysql_session, items) -> None:
        """商品やオプションの制約に違反すると注文が保存されない。

        Args:
            client_with_db: DBに接続するHTTPクライアント。
            mysql_session: 注文の有無を検証するセッション。
            items: 不正な商品・オプション明細。

        Returns:
            なし。
        """
        key = "order-invalid-catalog"
        response = client_with_db.post(
            PATH.format(visit_id=ACTIVE_VISIT), headers=_headers(key), json={"items": items},
        )
        assert response.status_code == 422
        assert mysql_session.scalar(select(MenuOrder).where(MenuOrder.idempotency_key == key)) is None

    @pytest.mark.usefixtures("insert_device_order_data")
    def test_with_db_recovers_concurrent_registration(self, client_with_db, mysql_session) -> None:
        """同時に未登録と判断した注文を1件だけ保存し、片方に既存結果を返す。

        Args:
            client_with_db: 参加する2リクエストのHTTPクライアント。
            mysql_session: 注文数を確認するセッション。

        Returns:
            なし。
        """
        key = "order-concurrent"
        gate = Barrier(2)
        original_lookup = DeviceOrderRepository.get_order_context

        def synchronized_lookup(repository, *args, **kwargs):
            """両リクエストで並行に実際のSELECTを実行する。"""
            rows = original_lookup(repository, *args, **kwargs)
            assert rows[0][3] is None
            gate.wait(timeout=10)
            return rows

        def send_order():
            """同じキーと内容で注文を送信する。"""
            return client_with_db.post(
                PATH.format(visit_id=ACTIVE_VISIT), headers=_headers(key), json={"items": [BURGER]},
            )

        with patch.object(DeviceOrderRepository, "get_order_context", synchronized_lookup):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(send_order) for _ in range(2)]
                first, second = (future.result(timeout=20) for future in futures)

        assert sorted([first.status_code, second.status_code]) == [200, 201]
        assert first.json() == second.json()
        stored = mysql_session.scalars(select(MenuOrder).where(MenuOrder.idempotency_key == key)).all()
        assert [row.menu_order_id for row in stored] == [first.json()["menu_order_id"]]

    @pytest.mark.usefixtures("insert_device_order_data")
    def test_with_db_rolls_back_after_writing_details(self, client_with_db, mysql_session) -> None:
        """明細保存後に処理が失敗すると注文全体が取り消される。

        Args:
            client_with_db: DBに接続するHTTPクライアント。
            mysql_session: ロールバック結果を検証するセッション。

        Returns:
            なし。
        """
        original_create = DeviceOrderRepository.create_order_items
        key = "order-rollback"
        url = PATH.format(visit_id=ACTIVE_VISIT)

        def write_then_fail(repository, *args, **kwargs):
            """明細をDBに反映してから例外を発生させる。"""
            original_create(repository, *args, **kwargs)
            raise RuntimeError("write failed")

        with patch.object(DeviceOrderRepository, "create_order_items", write_then_fail):
            response = client_with_db.post(url, headers=_headers(key), json={"items": [BURGER]})
        assert response.status_code == 500
        assert mysql_session.scalar(select(MenuOrder).where(MenuOrder.idempotency_key == key)) is None

        retry = client_with_db.post(url, headers=_headers(key), json={"items": [BURGER]})
        assert retry.status_code == 201
