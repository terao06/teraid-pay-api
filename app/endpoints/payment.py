from fastapi import APIRouter

from app.controllers.payment_controller import PaymentController
from app.middlewares.request_wrapper import request_rapper
from app.middlewares.response_wrapper import response_rapper
from app.models.requests.payment_create_request import PaymentCreateRequest
from app.models.requests.payment_create_from_face_request import PaymentCreateFromFaceRequest

payment_router = APIRouter()


@payment_router.post("/request")
@response_rapper()
@request_rapper()
def create_payment(request: PaymentCreateRequest):
    return PaymentController().create_and_execute_payment(request=request)


@payment_router.post("/request/with/face")
@response_rapper()
@request_rapper()
def create_payment_from_face(request: PaymentCreateFromFaceRequest):
    return PaymentController().create_and_execute_payment_from_face(
        request=request)


@payment_router.post("/request/{payment_request_id}/verify")
@response_rapper()
@request_rapper()
def verify_transaction_hash(payment_request_id: int):
    return PaymentController().verify_transaction_hash(
        payment_request_id=payment_request_id)
