"""端末が送る顔認証決済開始リクエストを検証する。"""

import base64
from binascii import Error as Base64Error
from functools import partial
from io import BytesIO
from typing import Annotated

from PIL import Image
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.core.utils.device_request import SIGNED_BIGINT_MAX, validate_decimal_id


class DeviceFacePaymentPathRequest(BaseModel):
    """顔認証決済開始のパスで指定された会計IDを検証する。

    Args:
        checkout_id: 端末で確認した会計のID。

    Returns:
        検証済みのパス入力。

    Raises:
        ValidationError: 会計IDの形式や範囲が不正な場合。
    """

    checkout_id: Annotated[
        int,
        Field(ge=1, le=SIGNED_BIGINT_MAX),
        BeforeValidator(partial(validate_decimal_id, label="checkout_id")),
    ]


class DeviceFacePaymentRequest(BaseModel):
    """端末で撮影した顔画像を受け付ける。

    Args:
        content: JPEGまたはPNGのBase64文字列。

    Returns:
        検証済みの顔認証決済開始リクエスト。
    """

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, content: str) -> str:
        """Base64を復号し、対応形式と画像サイズ、読み込み可否を確認する。

        Args:
            content: リクエストに含まれるBase64文字列。

        Returns:
            正常に読み込める画像のBase64文字列。

        Raises:
            ValueError: Base64や画像データが不正、または画像形式・寸法が対象外の場合。
        """
        try:
            decoded = base64.b64decode(content, validate=True)
            with Image.open(BytesIO(decoded), formats=("JPEG", "PNG")) as image:
                if max(image.size) > 2048:
                    raise ValueError("顔画像の縦横は2048ピクセル以内で指定してください。")
                image.load()
        except (Base64Error, OSError, SyntaxError, Image.DecompressionBombError):
            raise ValueError("顔画像はJPEGまたはPNGのBase64文字列で指定してください。") from None
        return content
