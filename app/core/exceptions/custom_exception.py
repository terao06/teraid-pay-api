"""APIで使用するドメイン例外とHTTP例外生成処理を提供する。"""

from fastapi import HTTPException


class StoreNotFoundException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class FaceEmbeddingNotFoundException(Exception):
    pass


class FaceEmbeddingAlreadyRegisterException(Exception):
    pass


class WalletConflictException(Exception):
    pass


class UnauthorizedException(Exception):
    pass


class StoreManagerInactiveException(Exception):
    pass


class MenuCategoryNotFoundException(Exception):
    pass


class MenuItemNotFoundException(Exception):
    pass


class DeviceActivationCodeInvalidException(Exception):
    pass


class DeviceActivationStateInvalidException(Exception):
    pass


class DeviceNotFoundException(Exception):
    pass


class DeviceAlreadyActivatedException(Exception):
    pass


class MenuImageInvalidException(Exception):
    pass


class MenuOptionConfigurationInvalidException(Exception):
    pass


class MenuCategoryImageInvalidException(Exception):
    pass


class InvalidImageError(Exception):
    pass


class WalletNotFoundException(Exception):
    pass


class WalletNotPermittedException(Exception):
    pass


class PaymentRequestNotFoundException(Exception):
    pass


class InsufficientFundsError(Exception):
    pass


class FaceNotFoundException(Exception):
    pass


class SameFaceFoundException(Exception):
    pass


class FaceConflictException(Exception):
    pass


class CustomHttpException:
    @staticmethod
    def get_http_exception(
        status_code: int,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> HTTPException:
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
        return HTTPException(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )
