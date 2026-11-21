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


class VisitSessionConflictException(Exception):
    pass


class VisitSessionCompletionConflictException(Exception):
    """未払い注文や決済処理のため来店セッションを終了できないことを表す。

    Args:
        message: 終了できない理由を示すメッセージ。

    Returns:
        来店セッションの終了条件を満たさないことを表す例外。
    """


class VisitSessionNotFoundException(Exception):
    pass


class DeviceOrderConflictException(Exception):
    """同じキーで異なる注文が登録済みであることを表す。

    Args:
        なし。

    Returns:
        冪等性キーの競合を表す例外。
    """


class DeviceCheckoutOrderNotFoundException(Exception):
    """指定した注文が認証済み端末の来店セッションに存在しないことを表す。

    Args:
        なし。

    Returns:
        対象注文が見つからない場合の例外。
    """


class DeviceCheckoutNotFoundException(Exception):
    """認証済み端末に紐づく会計が見つからないことを表す。

    Args:
        なし。

    Returns:
        会計へのアクセスを拒否する例外。
    """


class DeviceCheckoutConflictException(Exception):
    """来店セッションまたは注文の状態により会計を作成できないことを表す。

    Args:
        message: 端末に返す会計作成エラーの理由。

    Returns:
        会計作成時の競合を表す例外。
    """


class DeviceOrderInvalidException(Exception):
    """カートの内容が注文の登録条件を満たさないことを表す。

    Args:
        なし。

    Returns:
        注文内容の不備を表す例外。
    """


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


class WalletMismatchException(ValueError):
    """会計通貨とウォレットの通貨・チェーンが決済条件に合わないことを表す。

    Args:
        message: 通貨またはチェーンの不一致を説明するメッセージ。

    Returns:
        ウォレットの不一致を表す例外。
    """


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
