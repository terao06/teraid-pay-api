import base64
import binascii
from io import BytesIO

from PIL import Image, UnidentifiedImageError


class ImageUtil:
    """画像データの変換と形式判定を行うユーティリティ。"""

    @staticmethod
    def decode_base64_image(
        content: str,
        image_extension: str,
    ) -> bytes:
        """Base64画像を復号し、指定された拡張子と画像形式が一致することを検証する。

        Args:
            content: Base64形式の画像データ。
            image_extension: 画像データに対応する拡張子。

        Returns:
            復号した画像データ。
        """
        try:
            image_bytes = base64.b64decode(content, validate=True)
            with Image.open(BytesIO(image_bytes)) as image:
                image_format = image.format
                image.verify()
        except (binascii.Error, UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError("画像を読み込めません。") from exc

        expected_image_format = {
            "jpeg": "JPEG",
            "jpg": "JPEG",
            "png": "PNG",
        }.get(image_extension)
        if expected_image_format is None:
            raise ValueError("対応していない画像拡張子です。")
        if image_format != expected_image_format:
            raise ValueError("画像と拡張子が一致しません。")

        return image_bytes

    @staticmethod
    def get_content_type(image_extension: str) -> str:
        """画像拡張子に対応するContent-Typeを返す。

        Args:
            image_extension: Content-Typeを取得する画像拡張子。

        Returns:
            画像拡張子に対応するContent-Type。
        """
        content_type = {
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "png": "image/png",
        }.get(image_extension)
        if content_type is None:
            raise ValueError("対応していない画像拡張子です。")
        return content_type
