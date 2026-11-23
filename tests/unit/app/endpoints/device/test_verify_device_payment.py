"""端末の決済結果確認をHTTPと実MySQLで検証する。"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.config.device_auth import DeviceAuthConfig
from app.core.utils.device_auth import DeviceAuthUtil
from app.helpers.device_payment_chain_helper import DevicePaymentChainHelper
from app.models.mysql.menu_checkout import CheckoutStatus, MenuCheckout
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository
from app.services.device_payment_service import DevicePaymentService

_AUTH = DeviceAuthConfig("test-device-jwt-secret-at-least-32-characters", 300)
_PATH = "/device/checkouts/{}/payments/{}/verify"
_HASH = "0x" + "12" * 32


def _headers(device_id: int) -> dict[str, str]:
    """実際の端末認証に使うテスト用Bearerトークンを生成する。"""
    uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    return {"Authorization": f"Bearer {DeviceAuthUtil.create_access_token(uuid, _AUTH)}"}


def _start_payment(checkout_id: int, device_id: int) -> int:
    """既存の開始サービスで照会対象の試行を実DBへ登録する。"""
    uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    prepared = Mock(transaction_hash=_HASH)
    prepared.send.return_value = _HASH
    with (
        patch.object(DevicePaymentService, "_identify_payer", return_value=107),
        patch.object(DevicePaymentService, "_prepare_payment", return_value=prepared),
    ):
        result, status = DevicePaymentService().start_face_payment(uuid, checkout_id, "verify-dev", "")
    assert status == 201
    return result.payment_request_id


def _mock_successful_receipt(web3, mysql_engine, payment_id: int) -> None:
    """保存済みの試行と一致する成功レシートおよび決済イベントを返す。"""
    web3.eth.get_transaction_receipt.return_value = {"status": 1}
    with Session(mysql_engine) as session:
        payment = session.get(PaymentRequest, payment_id)
        event = {
            "address": "0x" + "55" * 20,
            "args": {
                "paymentId": DevicePaymentChainHelper.build_checkout_payment_id(payment.chain_id, payment.checkout_id),
                "token": "0x" + "44" * 20,
                "from": payment.user_wallet_address,
                "to": payment.store_wallet_address,
                "amount": 100_125_000_000_000_000_000,
            },
        }
    processor = web3.eth.contract.return_value
    processor.events.PaymentProcessed.return_value.process_receipt.return_value = [event]


class TestVerifyDevicePayment:
    """端末の認証と入力制約、DBに反映された決済結果を確認する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize(
        ("checkout", "payment"),
        [("0", "12"), ("1", "0"), ("1.0", "12"), ("1", "1.0"), ("1", "9223372036854775808")],
    )
    def test_rejects_invalid_path_parameters(self, client, checkout: str, payment: str) -> None:
        """会計IDと試行IDの不正な形式や範囲を認証・照会前に拒否する。

        Args:
            client: テスト用HTTPクライアント。
            checkout: リクエストの会計ID。
            payment: リクエストの決済試行ID。

        Returns:
            なし。
        """
        with patch("app.endpoints.device.DevicePaymentController.verify_payment") as verify:
            response = client.post(_PATH.format(checkout, payment))
        assert response.status_code == 422
        verify.assert_not_called()

    @pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
    def test_rejects_unauthenticated_request(self, client, headers: dict[str, str]) -> None:
        """Bearer認証を通過しない端末の決済照会を拒否する。

        Args:
            client: テスト用HTTPクライアント。
            headers: 認証情報が欠落または不正なヘッダー。

        Returns:
            なし。
        """
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=_AUTH),
            patch("app.endpoints.device.DevicePaymentController.verify_payment") as verify,
        ):
            response = client.post(_PATH.format(1, 2), headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        verify.assert_not_called()

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    @pytest.mark.parametrize(
        ("suffix", "result", "checkout_status", "order_status"),
        [
            (21, PaymentStatus.PAID, CheckoutStatus.PAID, OrderStatus.PAID),
            (22, PaymentStatus.TX_FAILED, CheckoutStatus.FAILED, OrderStatus.PENDING_PAYMENT),
        ],
    )
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_with_db_persists_result_and_replays_without_rpc(
        self, http_provider, web3_class, client_with_db, mysql_engine, suffix, result, checkout_status, order_status,
    ) -> None:
        """既存の個別決済と新規の一括決済の結果を確定し、再照会では保存済みの結果を返す。

        Args:
            client_with_db: 実MySQLを使うHTTPクライアント。
            mysql_engine: 状態を独立して確認するテスト用MySQL Engine。
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。
            suffix: ケース専用の端末、会計、来店セッションと注文のID末尾。
            result: RPC照会で確定した決済結果。
            checkout_status: 確定後の会計状態。
            order_status: 確定後の注文状態。

        Returns:
            なし。
        """
        checkout_id, device_id = 914000 + suffix, 911000 + suffix
        if suffix == 21:
            uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
            with patch.object(DevicePaymentService, "_identify_payer") as identify_payer:
                existing, status = DevicePaymentService().start_face_payment(uuid, checkout_id, "verify-dev", "")
            identify_payer.assert_not_called()
            assert (existing.payment_request_id, existing.status, status) == (916021, PaymentStatus.SUBMITTED, 200)
            payment_id = existing.payment_request_id
        else:
            payment_id = _start_payment(checkout_id, device_id)
        web3 = web3_class.return_value
        if result == PaymentStatus.PAID:
            _mock_successful_receipt(web3, mysql_engine, payment_id)
        else:
            block_hash = bytes.fromhex("ab" * 32)
            web3.eth.get_transaction_receipt.return_value = {"status": 0, "blockNumber": 80, "blockHash": block_hash}
            web3.eth.get_block.return_value = {"number": 80, "hash": block_hash}
            processor = web3.eth.contract.return_value
            processor.functions.processedPayments.return_value.call.return_value = False

        response = client_with_db.post(_PATH.format(checkout_id, payment_id), headers=_headers(device_id))
        replay = client_with_db.post(_PATH.format(checkout_id, payment_id), headers=_headers(device_id))
        expected = {
            "payment_request_id": payment_id, "status": result.value, "visit_session_status": "active",
            "has_unpaid_items": True,
        }
        assert (response.status_code, response.json()) == (200, expected)
        assert response.headers["Cache-Control"] == "no-store"
        assert (replay.status_code, replay.json()) == (200, expected)
        web3_class.assert_called_once_with(http_provider.return_value)
        web3.eth.get_transaction_receipt.assert_called_once_with(_HASH)
        with Session(mysql_engine) as session:
            assert session.get(PaymentRequest, payment_id).status == result
            assert session.get(MenuCheckout, checkout_id).status == checkout_status
            assert session.get(VisitSession, 912000 + suffix).status == VisitSessionStatus.ACTIVE
            order = session.get(MenuOrder, 913000 + suffix)
            assert order.status == order_status
            assert (order.paid_at is not None) == (result == PaymentStatus.PAID)
            if result == PaymentStatus.PAID:
                unselected = session.get(MenuOrder, 913025)
                assert unselected.status == OrderStatus.PENDING_PAYMENT
                assert unselected.paid_at is None

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_with_db_keeps_pending_and_filters_other_devices(
        self, http_provider, web3_class, client_with_db, mysql_engine,
    ) -> None:
        """対象会計の端末だけに決済試行を返し、RPC障害や未確定時の状態変更を防ぐ。

        Args:
            client_with_db: 実MySQLを使うHTTPクライアント。
            mysql_engine: 更新の有無を確認するMySQL Engine。
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。

        Returns:
            なし。
        """
        checkout_id, device_id = 914023, 911023
        payment_id = _start_payment(checkout_id, device_id)
        path = _PATH.format(checkout_id, payment_id)
        get_receipt = web3_class.return_value.eth.get_transaction_receipt
        get_receipt.side_effect = [TimeoutError(), None]
        assert client_with_db.post(path, headers=_headers(911024)).status_code == 404
        assert client_with_db.post(_PATH.format(checkout_id, 404), headers=_headers(device_id)).status_code == 404
        assert client_with_db.post(path, headers=_headers(device_id)).status_code == 503
        response = client_with_db.post(path, headers=_headers(device_id))
        assert get_receipt.call_count == 2
        assert http_provider.call_count == 2
        assert (response.status_code, response.json()) == (
            200, {
                "payment_request_id": payment_id, "status": "confirming", "visit_session_status": "checkout_processing",
                "has_unpaid_items": True,
            },
        )
        with Session(mysql_engine) as session:
            assert session.get(PaymentRequest, payment_id).status == PaymentStatus.SUBMITTED
            assert session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PROCESSING
            assert session.get(MenuOrder, 913023).paid_at is None
            assert session.get(VisitSession, 912023).status == VisitSessionStatus.CHECKOUT_PROCESSING

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_with_db_rolls_back_when_order_update_count_differs(
        self, http_provider, web3_class, client_with_db, mysql_engine,
    ) -> None:
        """注文更新後の件数検証に失敗すると、すべての更新を取り消す。

        Args:
            client_with_db: 実MySQLを使うHTTPクライアント。
            mysql_engine: ロールバックを確認するMySQL Engine。
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。

        Returns:
            なし。
        """
        checkout_id, device_id = 914024, 911024
        payment_id = _start_payment(checkout_id, device_id)
        update_orders = DevicePaymentRepository.mark_checkout_orders_paid

        def mismatched_count(repository, session, order_ids) -> int:
            """実際に更新した後、件数不一致を再現する。"""
            assert update_orders(repository, session, order_ids) == 1
            return 0

        _mock_successful_receipt(web3_class.return_value, mysql_engine, payment_id)
        with patch.object(DevicePaymentRepository, "mark_checkout_orders_paid", mismatched_count):
            response = client_with_db.post(_PATH.format(checkout_id, payment_id), headers=_headers(device_id))
        assert response.status_code == 500
        web3_class.assert_called_once_with(http_provider.return_value)
        with Session(mysql_engine) as session:
            assert session.get(PaymentRequest, payment_id).status == PaymentStatus.SUBMITTED
            assert session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PROCESSING
            assert session.get(VisitSession, 912024).status == VisitSessionStatus.CHECKOUT_PROCESSING
            assert session.get(MenuOrder, 913024).status == OrderStatus.PENDING_PAYMENT
            assert session.get(MenuOrder, 913024).paid_at is None

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_with_db_marks_order_paid_after_all_quantities_are_paid(
        self, http_provider, web3_class, client_with_db, mysql_engine,
    ) -> None:
        """同じ明細の分割と残りの明細を支払い、最後の確定時だけ注文を支払済みにする。

        Args:
            http_provider: 実ネットワークに接続しないHTTPProviderのモック。
            web3_class: チェーンRPC応答を設定するWeb3のモック。
            client_with_db: 実MySQLを使うHTTPクライアント。
            mysql_engine: コミット後の状態を確認するMySQL Engine。

        Returns:
            なし。
        """
        device_id = 911026
        headers = _headers(device_id)
        web3 = web3_class.return_value
        paths = []
        for checkout_id, has_unpaid_items in [(914026, True), (914027, True), (914028, False)]:
            payment_id = _start_payment(checkout_id, device_id)
            path = _PATH.format(checkout_id, payment_id)
            paths.append(path)
            _mock_successful_receipt(web3, mysql_engine, payment_id)
            response = client_with_db.post(path, headers=headers)

            assert (response.status_code, response.json()) == (
                200, {
                    "payment_request_id": payment_id, "status": "paid", "visit_session_status": "active",
                    "has_unpaid_items": has_unpaid_items,
                },
            )
            with Session(mysql_engine) as session:
                assert session.get(PaymentRequest, payment_id).status == PaymentStatus.PAID
                assert session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PAID
                order = session.get(MenuOrder, 913026)
                expected_status = OrderStatus.PENDING_PAYMENT if has_unpaid_items else OrderStatus.PAID
                assert order.status == expected_status
                assert (order.paid_at is None) is has_unpaid_items

        replay = client_with_db.post(paths[0], headers=headers)
        assert replay.status_code == 200
        assert replay.json()["status"] == "paid"
        assert replay.json()["has_unpaid_items"] is False
        assert http_provider.call_count == 3
        assert web3.eth.get_transaction_receipt.call_count == 3
