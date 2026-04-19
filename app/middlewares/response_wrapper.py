from functools import wraps
from pydantic import BaseModel
from fastapi import HTTPException


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
