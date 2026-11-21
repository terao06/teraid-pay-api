"""端末の顔認証決済開始をHTTPと実DBから検証する。"""

from decimal import Decimal
from hashlib import sha256
from unittest.mock import patch

from eth_utils import keccak
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config.device_auth import DeviceAuthConfig
from app.core.utils.device_auth import DeviceAuthUtil
from app.models.mysql.menu_checkout import CheckoutStatus, MenuCheckout
from app.models.mysql.menu_order import MenuOrder, OrderStatus
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.mysql.visit_session import VisitSession, VisitSessionStatus
from app.repositories.mysql.device_payment_repository import DevicePaymentRepository
from app.services.device_payment_service import DevicePaymentService
from tests.unit.app.endpoints.payment.test_create_payment_from_face import (
    FACE_IMAGE_PATH,
    build_base64_image,
    build_compact_face_content,
)

PATH = "/device/checkouts/{checkout_id}/payments/face"
AUTH = DeviceAuthConfig("test-device-jwt-secret-at-least-32-characters", 300)
KEY = "face-checkout-key"
SIGNED = b"signed-face-checkout"
TRANSACTION_HASH = "0x" + keccak(SIGNED).hex()


def _headers(device_id: int = 911001, key: str = KEY) -> dict[str, str]:
    """端末IDに対応するテスト用Bearerトークンと冪等性キーを返す。"""
    device_uuid = f"{device_id}00-0000-4000-8000-{device_id:012}"
    return {"Authorization": f"Bearer {DeviceAuthUtil.create_access_token(device_uuid, AUTH)}", "Idempotency-Key": key}


class TestStartFacePayment:
    """HTTP入力・応答と実DBへの登録および送信前後の状態を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("checkout_id, key, body", [
        ("0", KEY, None),
        ("789.0", KEY, None),
        ("9223372036854775808", KEY, None),
        ("789", None, None),
        ("789", " ", None),
        ("789", KEY, {}),
        ("789", KEY, {"content": "not base64"}),
        ("789", KEY, {"content": "aGVsbG8="}),
        ("789", KEY, {"content": "a" * 5001}),
        ("789", KEY, {"content": "aGVsbG8=", "amount": 99}),
    ])
    def test_rejects_invalid_input_before_mysql(self, client, checkout_id, key, body) -> None:
        """不正入力を422で拒否し、顔画像やキーを応答に含めない。

        Args:
            client: Endpointテスト用クライアント。
            checkout_id: 入力する会計ID。
            key: 冪等性キーまたはヘッダー省略を表すNone。
            body: JSON本体。Noneの場合はテスト画像を送る。

        Returns:
            なし。
        """
        headers = _headers(key=key or KEY)
        if key is None:
            del headers["Idempotency-Key"]
        with patch("app.services.device_payment_service.get_mysql_db") as mysql:
            response = client.post(
                PATH.format(checkout_id=checkout_id),
                json={"content": build_base64_image()} if body is None else body,
                headers=headers,
            )
        assert response.status_code == 422
        assert all("input" not in detail for detail in response.json()["detail"])
        mysql.assert_not_called()

    @pytest.mark.parametrize("token", [None, "invalid"])
    def test_rejects_unauthenticated_request_before_mysql(self, client, token) -> None:
        """欠落・不正トークンをMySQL接続前に401で拒否する。

        Args:
            client: Endpointクライアント。
            token: 値を送らないか無効なBearerトークン。

        Returns:
            なし。
        """
        headers = {"Idempotency-Key": KEY}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        with (
            patch("app.dependencies.device_auth.get_device_auth_config", return_value=AUTH),
            patch("app.services.device_payment_service.get_mysql_db") as mysql,
        ):
            response = client.post(PATH.format(checkout_id=789), json={"content": build_base64_image()}, headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        mysql.assert_not_called()

    @pytest.mark.usefixtures(
        "insert_face_checkout_payment_data", "insert_face_embeddings",
        "initialize_s3", "initialize_ssm", "use_local_s3_endpoint",
    )
    @pytest.mark.parametrize("suffix, amount, first_status, payment_status", [
        (1, Decimal("1500.375000"), 201, PaymentStatus.SUBMITTED),
        (2, Decimal("700.125000"), 202, PaymentStatus.REQUESTED),
        (3, Decimal("900.125000"), 400, PaymentStatus.ERROR),
        (6, Decimal("600.175000"), 202, PaymentStatus.REQUESTED),
    ])
    @patch("app.services.device_payment_service.Web3")
    @patch("app.services.device_payment_service.HTTPProvider")
    def test_with_db_starts_and_replays_the_same_payment(
        self, provider, web3_class, client_with_db, mysql_engine, suffix, amount, first_status, payment_status
    ) -> None:
        """顔照合、RPC送信前のコミット、同じ試行の再送、送信異常を検証する。

        Args:
            provider: モックのHTTPProvider。
            web3_class: モックのWeb3クラス。
            client_with_db: 実DB用クライアント。
            mysql_engine: APIと独立したMySQL接続のEngine。
            suffix: テスト専用データのID末尾。
            amount: 保存済み会計金額。
            first_status: 初回の期待HTTPステータス。
            payment_status: 保存する決済状態。

        Returns:
            なし。
        """
        checkout_id, visit_id, device_id = 914000 + suffix, 912000 + suffix, 911000 + suffix
        web3 = web3_class.return_value
        web3.to_checksum_address.side_effect = lambda address: address
        account = web3.eth.account.from_key.return_value
        account.address = "0x6666666666666666666666666666666666666666"
        account.sign_transaction.return_value.raw_transaction = SIGNED
        web3.eth.get_transaction_count.return_value = 7
        contract = web3.eth.contract.return_value
        contract.functions.balanceOf.return_value.call.return_value = 0 if first_status == 400 else 2000 * 10**18
        contract.functions.pay.return_value.build_transaction.return_value = {"nonce": 7}

        def send(raw_transaction: bytes) -> bytes:
            """RPCを呼んだ時点で別の接続から決済試行と状態を参照する。"""
            assert raw_transaction == SIGNED
            with Session(mysql_engine) as session:
                attempt = session.scalar(select(PaymentRequest).where(PaymentRequest.checkout_id == checkout_id))
                assert attempt.status == PaymentStatus.REQUESTED
                assert attempt.checkout_transaction_hash == TRANSACTION_HASH
                assert session.get(MenuCheckout, checkout_id).status == CheckoutStatus.PROCESSING
                assert session.get(VisitSession, visit_id).status == VisitSessionStatus.CHECKOUT_PROCESSING
            if suffix == 2:
                raise TimeoutError()
            return bytes.fromhex(TRANSACTION_HASH[2:])

        web3.eth.send_raw_transaction.side_effect = send
        path = PATH.format(checkout_id=checkout_id)
        headers = _headers(device_id)
        update_payment = DevicePaymentRepository.update_payment_request

        def update(repository, mysql_session, payment_request):
            """送信受付後に限って、決済状態をDBに記録できないケースを再現する。"""
            if suffix == 6 and payment_request.status == PaymentStatus.SUBMITTED:
                raise RuntimeError("simulated persistence failure")
            return update_payment(repository, mysql_session, payment_request)

        with patch.object(DevicePaymentRepository, "update_payment_request", autospec=True, side_effect=update):
            response = client_with_db.post(
                path, json={"content": build_compact_face_content(FACE_IMAGE_PATH)}, headers=headers
            )
        assert response.status_code == first_status, response.json()

        with Session(mysql_engine) as session:
            attempts = session.scalars(select(PaymentRequest).where(PaymentRequest.checkout_id == checkout_id)).all()
            assert len(attempts) == 1
            attempt = attempts[0]
            assert (attempt.status, attempt.user_id, attempt.store_id, attempt.amount) == (
                payment_status, 107, 9201, amount
            )
            assert attempt.idempotency_key_hash == sha256(KEY.encode()).digest()
            assert attempt.transaction_hash is None
            payment_request_id = attempt.payment_request_id
            expected = {"payment_request_id": payment_request_id, "status": payment_status.value}
            checkout = session.get(MenuCheckout, checkout_id)
            visit = session.get(VisitSession, visit_id)
            if first_status == 400:
                assert attempt.checkout_transaction_hash is None
                assert checkout.status == CheckoutStatus.FAILED
                assert visit.status == VisitSessionStatus.ACTIVE
                web3.eth.send_raw_transaction.assert_not_called()
            else:
                assert response.json() == expected
                assert response.headers["Cache-Control"] == "no-store"
                assert checkout.status == CheckoutStatus.PROCESSING
                assert visit.status == VisitSessionStatus.CHECKOUT_PROCESSING
                assert attempt.checkout_transaction_hash == TRANSACTION_HASH
                web3.eth.send_raw_transaction.assert_called_once_with(SIGNED)
                contract.functions.pay.assert_called_once_with(
                    keccak(text=f"teraid-pay:checkout:v1:11155111:{checkout_id}"),
                    "0x4444444444444444444444444444444444444444",
                    "0x6666666666666666666666666666666666666666",
                    "0x1111111111111111111111111111111111111111",
                    int(amount * 10**18),
                )
            order = session.get(MenuOrder, {1: 913001, 2: 913003, 3: 913004, 6: 913011}[suffix])
            assert order.status == OrderStatus.PENDING_PAYMENT
            assert order.paid_at is None

        body = {"content": build_base64_image()}
        replay = client_with_db.post(path, json=body, headers=headers)
        assert (replay.status_code, replay.json()) == (200, expected)
        if first_status != 400:
            replay = client_with_db.post(path, json=body, headers=_headers(device_id, "other-key"))
            assert (replay.status_code, replay.json()) == (200, expected)
            with patch("app.services.payment_service.Web3") as legacy_web3:
                legacy_result = client_with_db.post(f"/payment/request/{payment_request_id}/verify")
            assert legacy_result.status_code == 404
            legacy_web3.assert_not_called()
        if suffix == 1:
            competitor = client_with_db.post(PATH.format(checkout_id=914005), json=body, headers=headers)
            assert competitor.status_code == 409
        provider.assert_called_once()
        web3_class.assert_called_once()

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    def test_with_db_rolls_back_registration_when_writing_payment_fails(self, client_with_db, mysql_session) -> None:
        """試行登録に失敗した場合に会計・来店セッションの更新をロールバックする。

        Args:
            client_with_db: 実DB用クライアント。
            mysql_session: APIと独立したMySQLセッション。

        Returns:
            なし。
        """
        create_payment = DevicePaymentRepository.create_payment_request

        def fail_creation(repository, mysql_session, payment_request):
            """試行をフラッシュした直後にエラーを発生させる。"""
            create_payment(repository, mysql_session, payment_request)
            raise RuntimeError("simulated registration failure")

        with (
            patch.object(DevicePaymentService, "_identify_payer", return_value=107),
            patch.object(DevicePaymentRepository, "create_payment_request", autospec=True, side_effect=fail_creation),
            patch("app.services.device_payment_service.Web3") as web3,
        ):
            response = client_with_db.post(
                PATH.format(checkout_id=914007),
                json={"content": build_base64_image()},
                headers=_headers(911004),
            )
        assert response.status_code == 500
        web3.assert_not_called()
        assert mysql_session.get(MenuCheckout, 914007).status == CheckoutStatus.PENDING_CONFIRMATION
        assert mysql_session.get(VisitSession, 912004).status == VisitSessionStatus.ACTIVE
        assert mysql_session.scalar(select(PaymentRequest).where(PaymentRequest.checkout_id == 914007)) is None

    @pytest.mark.usefixtures("insert_face_checkout_payment_data")
    @pytest.mark.parametrize("device_id, checkout_id, status", [
        (911005, 914001, 401),
        (911004, 914001, 404),
        (911001, 999999, 404),
        (911004, 914004, 409),
    ])
    def test_with_db_rejects_unavailable_or_stale_checkout(
        self, client_with_db, device_id, checkout_id, status
    ) -> None:
        """停止端末、対象外の会計、追加注文で古くなった明細を顔照合前に拒否する。

        Args:
            client_with_db: 実DB用クライアント。
            device_id: 操作する端末ID。
            checkout_id: 決済を要求する会計ID。
            status: 期待するHTTPステータス。

        Returns:
            なし。
        """
        with patch.object(DevicePaymentService, "_identify_payer") as identify_payer:
            response = client_with_db.post(
                PATH.format(checkout_id=checkout_id),
                json={"content": build_base64_image()},
                headers=_headers(device_id),
            )
        assert response.status_code == status
        identify_payer.assert_not_called()
