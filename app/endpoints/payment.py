from fastapi import APIRouter
from app.controllers.payment_controller import PaymentController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.payment_create_request import PaymentCreateRequest

payment_router = APIRouter()


@payment_router.post("/request")
@response_rapper()
@request_rapper()
def create_payment(request: PaymentCreateRequest):
    """送金リクエストを情報作成する。

    Args:
        request: 決済情報作成リクエスト情報。

    Returns:
        作成した決済情報リクエスト情報。
    """
    return PaymentController().create_payment_request(request=request)


@payment_router.post("/request/{payment_request_id}/execute")
@response_rapper()
@request_rapper()
def execute_payment(payment_request_id: int):
    """送金リクエストを情報作成する。

    Args:
        request: 決済情報作成リクエスト情報。

    Returns:
        作成した決済情報リクエスト情報。
    """
    return PaymentController().execute_payment(
        payment_request_id=payment_request_id)


@payment_router.post("/request/{payment_request_id}/verify")
@response_rapper()
@request_rapper()
def verify_transaction_hash(payment_request_id: int):
    """送金リクエストを情報作成する。

    Args:
        request: 決済情報作成リクエスト情報。

    Returns:
        作成した決済情報リクエスト情報。
    """
    return PaymentController().verify_transaction_hash(
        payment_request_id=payment_request_id)
