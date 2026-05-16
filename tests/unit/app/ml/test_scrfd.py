from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from scrfd import Face

from app.core.exceptions.custom_exception import FaceNotFoundException, SameFaceFoundException
from app.ml.scrfd import Scrfd


TEST_DATA_ROOT = Path(__file__).resolve().parents[2] / "test_data"
SCRFD_WEIGHT_PATH = TEST_DATA_ROOT / "s3" / "buckets" / "weights" / "scrfd" / "scrfd.onnx"
SCRFD_IMAGE_ROOT = TEST_DATA_ROOT / "images" / "scrfd"


class TestScrfdGetFace:
    def test_get_face_returns_detected_face_with_real_model(self) -> None:
        weight_bytes = BytesIO(SCRFD_WEIGHT_PATH.read_bytes())
        weight_bytes.seek(4)
        image = Image.open(SCRFD_IMAGE_ROOT / "one_face.png")

        face = Scrfd(weight_bytes=weight_bytes).get_face(image=image)

        assert isinstance(face, Face)
        assert face.bbox.upper_left.x < face.bbox.lower_right.x
        assert face.bbox.upper_left.y < face.bbox.lower_right.y
        assert face.probability > 0.4

    def test_get_face_raises_face_not_found_with_real_model(self) -> None:
        weight_bytes = BytesIO(SCRFD_WEIGHT_PATH.read_bytes())
        image = Image.open(SCRFD_IMAGE_ROOT / "not_has_faces.jpeg")

        with pytest.raises(FaceNotFoundException):
            Scrfd(weight_bytes=weight_bytes).get_face(image=image)

    def test_get_face_raises_same_face_found_with_real_model(self) -> None:
        weight_bytes = BytesIO(SCRFD_WEIGHT_PATH.read_bytes())
        image = Image.open(SCRFD_IMAGE_ROOT / "multi_faces.jpg")

        with pytest.raises(SameFaceFoundException):
            Scrfd(weight_bytes=weight_bytes).get_face(image=image)
