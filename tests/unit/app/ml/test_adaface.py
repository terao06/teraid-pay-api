from pathlib import Path

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")

from app.ml.adaface import AdaFace


TEST_DATA_ROOT = Path(__file__).resolve().parents[2] / "test_data"
ADAFACE_WEIGHT_PATH = (
    TEST_DATA_ROOT / "s3" / "buckets" / "weights" / "adaface" / "adaface_ir50_ms1mv2.ckpt"
)
TEST_FACE_PATH = TEST_DATA_ROOT / "images" / "adaface" / "test_face.png"


def load_test_face_image() -> Image.Image:
    return Image.open(TEST_FACE_PATH).convert("RGB").resize((112, 112))


class TestAdaFaceGetEmbedding:
    def test_get_embedding_returns_normalized_embedding_with_real_model(self) -> None:
        weight_bytes = ADAFACE_WEIGHT_PATH.read_bytes()
        image = load_test_face_image()

        embedding = AdaFace(weight_bytes=weight_bytes).get_embedding(image=image)

        assert len(embedding) == 512
        assert np.isfinite(embedding).all()
        assert np.linalg.norm(embedding) == pytest.approx(1.0, abs=1e-5)

    def test_get_embedding_can_be_called_multiple_times_with_real_model(self) -> None:
        weight_bytes = ADAFACE_WEIGHT_PATH.read_bytes()
        model = AdaFace(weight_bytes=weight_bytes)
        image = load_test_face_image()

        first_embedding = model.get_embedding(image=image)
        second_embedding = model.get_embedding(image=image)

        assert first_embedding == pytest.approx(second_embedding)


class TestAdaFacePreprocess:
    def test_to_bgr_input_normalizes_rgb_pil_image(self) -> None:
        image = Image.fromarray(
            np.array([[[255, 128, 0], [0, 128, 255]]], dtype=np.uint8),
            mode="RGB",
        )

        tensor = AdaFace._to_bgr_input(image)

        assert tensor.shape == (1, 3, 1, 2)
        assert torch.allclose(tensor[0, :, 0, 0], torch.tensor([-1.0, 0.00392163, 1.0]))
        assert torch.allclose(tensor[0, :, 0, 1], torch.tensor([1.0, 0.00392163, -1.0]))
