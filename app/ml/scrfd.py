from io import BytesIO
from pathlib import Path

from onnxruntime import InferenceSession
from PIL import Image
from scrfd import SCRFD, Face, Threshold

from app.core.exceptions.custom_exception import FaceNotFoundException, SameFaceFoundException
from app.core.utils.logging import TeraidPayApiLog

ML_ROOT = Path(__file__).resolve().parent


class Scrfd:
    def __init__(self, weight_bytes: BytesIO):
        self.weight_bytes = weight_bytes

    def get_face(self, image: Image.Image) -> Face:
        """画像から顔を1件だけ検出して返す。

        Args:
            image: 顔検出の対象となる画像。

        Returns:
            検出された顔情報。

        Raises:
            FaceNotFoundException: 顔を検出できなかった場合。
            SameFaceFoundException: 顔を複数検出した場合。
        """
        self.weight_bytes.seek(0)
        session = InferenceSession(self.weight_bytes.read())
        model = SCRFD.from_session(session)
        faces = model.detect(image=image, threshold=Threshold(probability=0.4))

        if len(faces) == 0:
            TeraidPayApiLog.warning("顔を検出できませんでした。")
            raise FaceNotFoundException("顔が検出されませんでした。")
        if len(faces) > 1:
            TeraidPayApiLog.warning(f"顔が複数検出されました。 顔検出数 = {len(faces)}")
            raise SameFaceFoundException("顔が検出されませんでした。")

        return faces[0]
