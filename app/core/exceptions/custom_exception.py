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
    """認証店舗に対象メニュー商品が存在しないことを表す。

    Args:
        message: 例外の詳細メッセージ。省略可能。

    Returns:
        メニュー商品未存在を表す例外。
    """


class DeviceActivationStateInvalidException(Exception):
    """未有効化デバイスを利用可能に変更しようとしたことを表す。

    Args:
        message: 例外の詳細メッセージ。省略可能。

    Returns:
        デバイスの有効化状態が不正であることを表す例外。
    """


class DeviceNotFoundException(Exception):
    """認証店舗に対象デバイスが存在しないことを表す。

    Args:
        message: 例外の詳細メッセージ。省略可能。

    Returns:
        デバイスが存在しないことを表す例外。
    """


class MenuImageInvalidException(Exception):
    pass


class MenuOptionConfigurationInvalidException(Exception):
    """指定されたオプションIDの所属関係が不正であることを表す。

    Args:
        message: 例外の詳細メッセージ。省略可能。

    Returns:
        不正なメニューオプション構成を表す例外。
    """


class MenuCategoryImageInvalidException(Exception):
    pass


class InvalidImageError(Exception):
    """共通画像差し替え処理で画像を読み込めなかったことを表す。

    Args:
        message: 例外の詳細メッセージ。省略可能。

    Returns:
        不正な画像を表す例外。
    """


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
