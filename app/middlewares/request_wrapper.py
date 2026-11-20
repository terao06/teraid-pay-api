"""APIのリクエストログと入力検証エラーの応答を扱う。"""

import json
from functools import wraps

from fastapi import Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.utils.logging import TeraidPayApiLog


def _convert_to_dict(obj):
    """オブジェクトをログ出力用の辞書へ変換する。

    Args:
        obj: 変換対象のオブジェクト。

    Returns:
        辞書化された値、またはそのままの値。
    """
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    else:
        return obj


def request_rapper(*, log_parameters: bool = True):
    """エンドポイントの呼び出しをログに記録するデコレーターを返す。

    Args:
        log_parameters: 関数名に加え、マスキングしたリクエストの引数を記録するか。

    Returns:
        関数実行前にリクエスト情報を記録するデコレーター。
    """
    def decorator(func):
        """対象関数をラップするデコレーター本体。

        Args:
            func: ラップ対象の関数。

        Returns:
            リクエストログ出力を追加した関数。
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            """リクエスト情報を記録してから元の関数を実行する。

            Args:
                *args: 元の関数へ渡す位置引数。
                **kwargs: 元の関数へ渡すキーワード引数。

            Returns:
                元の関数の返り値。
            """
            func_name = func.__name__
            TeraidPayApiLog.info(f"Function: {func_name}")
            if not log_parameters:
                return func(*args, **kwargs)

            # Pydanticモデルや基本型のパラメータをログ出力
            log_params = {}
            for key, value in kwargs.items():
                # Requestオブジェクトなどの大きなオブジェクトは除外
                if key not in ['request', 'response', 'db', 'session']:
                    try:
                        log_params[key] = _convert_to_dict(value)
                    except Exception as e:
                        log_params[key] = str(type(value))
            
            if log_params:
                # センシティブな情報をマスキング
                masked_params = TeraidPayApiLog.mask_sensitive_data(log_params)
                # JSON形式で出力
                try:
                    json_str = json.dumps(masked_params, ensure_ascii=False, indent=None)
                    TeraidPayApiLog.info(f"Request parameters: {json_str}")
                except (TypeError, ValueError) as e:
                    # JSON化できない場合は文字列化
                    TeraidPayApiLog.info(f"Request parameters: {masked_params}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def request_device_rapper():
    """端末用APIに、関数名だけを記録するデコレーターを返す。

    Args:
        なし。

    Returns:
        関数名を記録し、入力検証エラー時に入力値を除外する対象として登録するデコレーター。
    """
    log_request = request_rapper(log_parameters=False)

    def decorator(func):
        """入力検証前に端末用APIを識別できる属性を付与する。"""
        wrapped = log_request(func)
        wrapped._omit_validation_input = True
        return wrapped

    return decorator


async def handle_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """端末用APIの422レスポンスを入力値を含まない形式に整える。

    Args:
        request: 入力検証に失敗したリクエスト。
        error: 入力検証のエラー情報。

    Returns:
        端末用APIでは位置・種別・メッセージを含む422レスポンス。
        その他のAPIではFastAPIの標準レスポンス。
    """
    endpoint = request.scope.get("endpoint")
    if not getattr(endpoint, "_omit_validation_input", False):
        return await request_validation_exception_handler(request, error)

    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {key: entry[key] for key in ("loc", "type", "msg")}
                for entry in error.errors()
            ]
        },
    )
