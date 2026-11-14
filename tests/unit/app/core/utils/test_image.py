import base64
from io import BytesIO

from PIL import Image
import pytest

from app.core.utils.image import ImageUtil


def build_base64_image(format: str) -> tuple[str, bytes]:
    """指定形式のテスト用画像とBase64文字列を生成する。"""
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format=format)
        image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode("ascii"), image_bytes


class TestDecodeBase64Image:
    """ImageUtil.decode_base64_imageの単体テスト。"""

    @pytest.mark.parametrize(
        ("image_format", "image_extension"),
        [
            ("JPEG", "jpeg"),
            ("JPEG", "jpg"),
            ("PNG", "png"),
        ],
    )
    def test_decode_base64_image(
        self,
        image_format: str,
        image_extension: str,
    ) -> None:
        """Base64画像を復号して元の画像データを返すことを確認する。"""
        content, expected_image_bytes = build_base64_image(format=image_format)

        result = ImageUtil.decode_base64_image(
            content=content,
            image_extension=image_extension,
        )

        assert result == expected_image_bytes

    def test_raise_when_content_is_not_base64(self) -> None:
        """Base64として不正な文字列を指定した場合にValueErrorを送出することを確認する。"""
        with pytest.raises(ValueError, match="画像を読み込めません。"):
            ImageUtil.decode_base64_image(
                content="invalid-image",
                image_extension="png",
            )

    def test_raise_when_image_and_extension_do_not_match(self) -> None:
        """画像形式と拡張子が一致しない場合にValueErrorを送出することを確認する。"""
        content, _ = build_base64_image(format="PNG")

        with pytest.raises(ValueError, match="画像と拡張子が一致しません。"):
            ImageUtil.decode_base64_image(
                content=content,
                image_extension="jpeg",
            )

    def test_raise_when_extension_is_not_supported(self) -> None:
        """未対応の拡張子を指定した場合にValueErrorを送出することを確認する。"""
        content, _ = build_base64_image(format="PNG")

        with pytest.raises(ValueError, match="対応していない画像拡張子です。"):
            ImageUtil.decode_base64_image(
                content=content,
                image_extension="gif",
            )


class TestGetContentType:
    """ImageUtil.get_content_typeの単体テスト。"""

    @pytest.mark.parametrize(
        ("image_extension", "expected_content_type"),
        [
            ("jpeg", "image/jpeg"),
            ("jpg", "image/jpeg"),
            ("png", "image/png"),
        ],
    )
    def test_get_content_type(
        self,
        image_extension: str,
        expected_content_type: str,
    ) -> None:
        """画像拡張子に対応するContent-Typeを返すことを確認する。"""
        result = ImageUtil.get_content_type(image_extension=image_extension)

        assert result == expected_content_type

    def test_raise_when_extension_is_not_supported(self) -> None:
        """未対応の拡張子を指定した場合にValueErrorを送出することを確認する。"""
        with pytest.raises(ValueError, match="対応していない画像拡張子です。"):
            ImageUtil.get_content_type(image_extension="gif")
