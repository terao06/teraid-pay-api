"""端末用レスポンスデコレーターのヘッダー設定と返却結果を検証する。"""

from fastapi import HTTPException, Response
import pytest

from app.middlewares.response_wrapper import response_device_rapper


def test_device_response_sets_no_store_and_returns_original_result() -> None:
    """成功時にキャッシュを禁止し、端末APIの元の結果を返す。"""

    @response_device_rapper()
    def endpoint(response: Response, payload: dict[str, str]) -> dict[str, str]:
        """指定したレスポンスに別のヘッダーを設定し、ペイロードを返す。"""
        response.headers["X-Request-ID"] = "request-id"
        return payload

    response = Response()
    payload = {"device_uuid": "device-uuid", "device_credential": "device-credential"}

    assert endpoint(response=response, payload=payload) is payload
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "request-id"


def test_device_response_preserves_endpoint_errors() -> None:
    """エンドポイントのHTTP例外を呼び出し元へ伝える。"""
    error = HTTPException(status_code=400, detail="invalid activation code")

    @response_device_rapper()
    def endpoint(response: Response) -> None:
        """有効化コードが無効な場合のHTTP例外を発生させる。"""
        raise error

    response = Response()

    with pytest.raises(HTTPException) as caught:
        endpoint(response=response)

    assert caught.value is error
    assert "cache-control" not in response.headers
