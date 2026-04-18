from fastapi import HTTPException


class StoreNotFoundException(Exception):
    pass


class WalletConflictException(Exception):
    pass


class UnauthorizedException(Exception):
    pass


class CustomHttpException:
    @staticmethod
    def get_http_exception(status_code: int, message: str) -> HTTPException:
        """共通エラーレスポンス形式の HTTPException を生成する。

        Args:
            status_code: HTTP ステータスコード。
            message: レスポンスに含めるエラーメッセージ。

        Returns:
            共通フォーマットの detail を持つ HTTPException。
        """
        detail = {
            "status": "error",
            "message": message
        }
        return HTTPException(status_code=status_code, detail=detail)
