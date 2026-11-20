"""通常APIと端末用APIのリクエストログと入力エラー応答を検証する。"""

import asyncio
import json
from unittest.mock import call, patch

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.middlewares.request_wrapper import (
    handle_request_validation_error,
    request_device_rapper,
    request_rapper,
)


@pytest.mark.parametrize(
    ("decorator", "expected_calls"),
    [
        (
            request_rapper,
            [
                call("Function: endpoint"),
                call('Request parameters: {"device_name": "sample-device"}'),
            ],
        ),
        (request_device_rapper, [call("Function: endpoint")]),
    ],
)
@patch("app.middlewares.request_wrapper.TeraidPayApiLog.info")
def test_request_logging(mock_info, decorator, expected_calls) -> None:
    """通常APIは引数も記録し、端末用APIは関数名だけを記録する。

    Args:
        mock_info: ロガーの呼び出しを記録するモック。
        decorator: エンドポイントに適用するデコレーターの生成関数。
        expected_calls: 期待するログ出力。

    Returns:
        なし。
    """
    @decorator()
    def endpoint(device_name: str) -> str:
        """呼び出し時に受け取った端末名を返す。"""
        return device_name

    assert endpoint(device_name="sample-device") == "sample-device"
    assert mock_info.call_args_list == expected_calls


@pytest.mark.parametrize(
    ("decorator", "includes_input"),
    [(request_rapper, True), (request_device_rapper, False)],
)
def test_validation_error_includes_input_only_for_standard_requests(
    decorator,
    includes_input: bool,
) -> None:
    """入力検証エラーの応答を確認する。

    Args:
        decorator: エンドポイントに適用するデコレーター。
        includes_input: 422の応答に入力値が含まれることを期待するか。

    Returns:
        なし。
    """
    @decorator()
    def endpoint() -> None:
        """入力検証エラー時にエンドポイントには到達しない。"""
        pytest.fail("Endpoint should not be called during validation error handling")

    request = Request({"type": "http", "endpoint": endpoint})
    error = RequestValidationError(
        [
            {
                "loc": ("body", "activation_code"),
                "type": "string_pattern_mismatch",
                "msg": "Invalid format",
                "input": "test-activation-code",
            }
        ]
    )

    response = asyncio.run(handle_request_validation_error(request, error))

    assert response.status_code == 422
    detail = json.loads(response.body)["detail"][0]
    assert detail["loc"] == ["body", "activation_code"]
    assert detail["type"] == "string_pattern_mismatch"
    assert detail["msg"] == "Invalid format"
    assert ("input" in detail) is includes_input
