from pathlib import Path
from unittest.mock import Mock, patch

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
        weight_bytes = SCRFD_WEIGHT_PATH.read_bytes()
        image = Image.open(SCRFD_IMAGE_ROOT / "one_face.png")

        face = Scrfd(weight_bytes=weight_bytes).get_face(image=image)

        assert isinstance(face, Face)
        assert face.bbox.upper_left.x < face.bbox.lower_right.x
        assert face.bbox.upper_left.y < face.bbox.lower_right.y
        assert face.probability > 0.4

    def test_get_face_raises_face_not_found_with_real_model(self) -> None:
        weight_bytes = SCRFD_WEIGHT_PATH.read_bytes()
        image = Image.open(SCRFD_IMAGE_ROOT / "not_has_faces.jpeg")

        with pytest.raises(FaceNotFoundException):
            Scrfd(weight_bytes=weight_bytes).get_face(image=image)

    def test_get_face_raises_same_face_found_with_real_model(self) -> None:
        weight_bytes = SCRFD_WEIGHT_PATH.read_bytes()
        image = Image.open(SCRFD_IMAGE_ROOT / "multi_faces.jpg")

        with pytest.raises(SameFaceFoundException):
            Scrfd(weight_bytes=weight_bytes).get_face(image=image)


class TestScrfdExecutionProvider:
    @pytest.mark.parametrize(
        ("device", "available_providers", "expected_providers"),
        [
            ("cpu", ["CPUExecutionProvider"], ["CPUExecutionProvider"]),
            ("auto", ["CPUExecutionProvider"], ["CPUExecutionProvider"]),
            (
                "auto",
                ["CUDAExecutionProvider", "CPUExecutionProvider"],
                ["CUDAExecutionProvider", "CPUExecutionProvider"],
            ),
            (
                "cuda",
                ["CUDAExecutionProvider", "CPUExecutionProvider"],
                ["CUDAExecutionProvider"],
            ),
            (
                "gpu",
                ["CUDAExecutionProvider", "CPUExecutionProvider"],
                ["CUDAExecutionProvider"],
            ),
        ],
    )
    def test_get_execution_providers_returns_provider_for_selected_device(
        self,
        device,
        available_providers,
        expected_providers,
    ) -> None:
        with patch("app.ml.scrfd.ort.get_available_providers", return_value=available_providers):
            assert Scrfd._get_execution_providers(device) == expected_providers

    def test_get_execution_providers_raises_error_when_cuda_is_unavailable(self) -> None:
        with patch("app.ml.scrfd.ort.get_available_providers", return_value=["CPUExecutionProvider"]):
            with pytest.raises(ValueError, match="CUDAExecutionProvider is not available"):
                Scrfd._get_execution_providers("cuda")

    def test_get_execution_providers_raises_error_when_device_is_invalid(self) -> None:
        with pytest.raises(ValueError, match="SCRFD device"):
            Scrfd._get_execution_providers("invalid")

    @patch("app.ml.scrfd.SCRFD")
    @patch("app.ml.scrfd.InferenceSession")
    @patch("app.ml.scrfd.ort.get_available_providers")
    def test_get_face_passes_selected_provider_to_inference_session(
        self,
        mock_get_available_providers,
        mock_inference_session,
        mock_scrfd_class,
    ) -> None:
        mock_get_available_providers.return_value = ["CPUExecutionProvider"]
        face = Mock()
        model = Mock()
        model.detect.return_value = [face]
        mock_scrfd_class.from_session.return_value = model
        image = Image.new("RGB", (112, 112), color=(255, 255, 255))

        result = Scrfd(weight_bytes=b"onnx-weight", device="cpu").get_face(image=image)

        assert result is face
        mock_inference_session.assert_called_once_with(
            b"onnx-weight",
            providers=["CPUExecutionProvider"],
        )
