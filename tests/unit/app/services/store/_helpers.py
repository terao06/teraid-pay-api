import base64
from io import BytesIO

from PIL import Image


def build_menu_image(format: str = "PNG") -> str:
    """テスト用メニュー画像をBase64文字列で生成する。"""
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
