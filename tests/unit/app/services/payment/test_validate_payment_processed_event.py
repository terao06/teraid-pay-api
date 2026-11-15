from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.payment_service import PaymentService


class TestValidatePaymentProcessedEvent:
    """PaymentService._validate_payment_processed_event tests."""

    token_contract_address = "0x1111111111111111111111111111111111111111"
    user_wallet_address = "0x2222222222222222222222222222222222222222"
    store_wallet_address = "0x3333333333333333333333333333333333333333"

    def _build_payment_request(self, payment_request_id=501, amount=1500):
        return SimpleNamespace(
            payment_request_id=payment_request_id,
            chain_id=11155111,
            user_wallet_address=self.user_wallet_address,
            store_wallet_address=self.store_wallet_address,
            amount=amount,
            expires_at=datetime(2026, 4, 12, 12, 10, 0),
        )

    def _build_payment_processor(self, events):
        payment_processor = Mock()
        payment_processor.events.PaymentProcessed.return_value.process_receipt.return_value = events
        return payment_processor

    def _build_event(self, **overrides):
        args = {
            "paymentId": int(501).to_bytes(32, byteorder="big"),
            "token": self.token_contract_address,
            "from": self.user_wallet_address,
            "to": self.store_wallet_address,
            "amount": 1500 * 10**18,
            "operator": "0x4444444444444444444444444444444444444444",
        }
        args.update(overrides)
        return {"args": args}

    def test_validate_payment_processed_event_returns_true_when_event_matches_payment_request(self) -> None:
        """transaction の contract/from/input が payment_request と一致する場合 True を返す。"""
        payment_request = self._build_payment_request()
        receipt = SimpleNamespace()
        payment_processor = self._build_payment_processor([self._build_event()])

        result = PaymentService()._validate_payment_processed_event(
            payment_request=payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address=self.token_contract_address,
        )

        assert result is True

    @pytest.mark.parametrize(
        ("payment_request_overrides", "event_overrides", "token_contract_address"),
        [
            ({"payment_request_id": 502}, {}, token_contract_address),
            ({}, {"token": "0x4444444444444444444444444444444444444444"}, token_contract_address),
            ({}, {"from": "0x5555555555555555555555555555555555555555"}, token_contract_address),
            ({}, {"to": "0x6666666666666666666666666666666666666666"}, token_contract_address),
            ({"amount": 1501}, {}, token_contract_address),
        ],
        ids=[
            "payment-id-mismatch",
            "token-address-mismatch",
            "from-address-mismatch",
            "to-address-mismatch",
            "amount-mismatch",
        ],
    )
    def test_validate_payment_processed_event_returns_false_when_event_does_not_match_payment_request(
        self,
        payment_request_overrides,
        event_overrides,
        token_contract_address,
    ) -> None:
        """transaction の検証対象値が一致しない場合 False を返す。"""
        payment_request = self._build_payment_request(**payment_request_overrides)
        receipt = SimpleNamespace()
        payment_processor = self._build_payment_processor([self._build_event(**event_overrides)])

        result = PaymentService()._validate_payment_processed_event(
            payment_request=payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address=token_contract_address,
        )

        assert result is False
