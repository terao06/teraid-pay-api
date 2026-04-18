from functools import wraps
from app.core.utils.logging import TeraidPayApiLog
import json


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


def request_rapper():
    """リクエスト内容をログ出力するデコレーターを返す。

    Args:
        なし。

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
