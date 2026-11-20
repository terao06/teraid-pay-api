"""APIエンドポイントのレスポンスを整形する。"""

from functools import wraps

from fastapi import HTTPException, Response
from pydantic import BaseModel


def response_rapper(data_key: str = "data"):
    """レスポンスを共通形式で包むデコレーターを返す。

    Args:
        data_key: 成功時データを格納するキー名。

    Returns:
        レスポンス整形を行うデコレーター。
    """
    def decorator(func):
        """対象関数を共通レスポンス形式に変換する。

        Args:
            func: ラップ対象の関数。

        Returns:
            レスポンス整形を行う関数。
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            """元の関数結果を共通レスポンス形式へ変換する。

            Args:
                *args: 元の関数へ渡す位置引数。
                **kwargs: 元の関数へ渡すキーワード引数。

            Returns:
                成功時は共通形式のレスポンス。
            """
            try:
                result = func(*args, **kwargs)
                # Pydantic モデルのインスタンスの場合
                if isinstance(result, BaseModel):
                    result = result.model_dump()

                # リスト内の Pydantic モデルも辞書に変換
                elif isinstance(result, list):
                    result = [item.model_dump() if isinstance(item, BaseModel) else item for item in result]

                # 成功した場合のレスポンス
                response = {
                    "status": "success",
                    data_key: result,
                }
                return response

            except HTTPException as e:
                raise e
            except Exception as e:
                raise e
        return wrapper
    return decorator


def response_device_rapper():
    """端末用APIの成功レスポンスにキャッシュ制御を追加するデコレーターを返す。

    Args:
        なし。

    Returns:
        成功時にキャッシュを禁止し、端末用APIの結果を返すデコレーター。
    """
    def decorator(func):
        """先頭引数にResponseを受け取る端末用エンドポイントをラップする。

        Args:
            func: FastAPIのResponseを先頭引数に受け取るエンドポイント。

        Returns:
            成功時にキャッシュ制御を設定するエンドポイント。
        """
        @wraps(func)
        def wrapper(response: Response, *args, **kwargs):
            """元の関数を実行し、成功レスポンスのキャッシュを禁止する。"""
            result = func(response, *args, **kwargs)
            response.headers["Cache-Control"] = "no-store"
            return result

        return wrapper
    return decorator
