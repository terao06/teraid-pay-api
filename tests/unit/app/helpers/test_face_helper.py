from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image

from app.helpers.face_helper import (
    FACE_ALIGNMENT_SIZE,
    REFERENCE_FIVE_POINT_LANDMARKS,
    FaceHelper,
    FaceImage,
)


def _point(x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y)


class TestFaceHelperGetFaceLandmark:
    @patch("app.helpers.face_helper.Scrfd")
    def test__get_face_landmark_returns_cropped_face_and_relative_landmarks(
        self,
        mock_scrfd,
    ) -> None:
        """検出した顔のbboxで画像を切り出し、ランドマークを切り出し後の座標へ変換すること。"""
        weight_bytes = b"onnx-weight"
        image = Image.new("RGB", (100, 120), color=(255, 255, 255))
        face = Mock()
        scrfd = Mock()

        face.bbox = SimpleNamespace(
            upper_left=_point(-3.2, 10.8),
            lower_right=_point(80.1, 90.2),
        )
        face.keypoints = SimpleNamespace(
            left_eye=_point(20.5, 30.0),
            right_eye=_point(60.0, 31.5),
            nose=_point(43.0, 51.0),
            left_mouth=_point(25.0, 75.5),
            right_mouth=_point(62.5, 76.0),
        )
        mock_scrfd.return_value = scrfd
        scrfd.get_face.return_value = face

        result = FaceHelper._get_face_landmark(weight_bytes=weight_bytes, image=image)

        mock_scrfd.assert_called_once_with(
            weight_bytes=weight_bytes,
            device="cuda",
        )
        scrfd.get_face.assert_called_once_with(image=image)
        assert result.image.size == (81, 81)
        assert result.landmarks == (
            (20.5, 20.0),
            (60.0, 21.5),
            (43.0, 41.0),
            (25.0, 65.5),
            (62.5, 66.0),
        )

    @patch("app.helpers.face_helper.Scrfd")
    def test__get_face_landmark_uses_cuda_device(
        self,
        mock_scrfd,
    ) -> None:
        weight_bytes = b"onnx-weight"
        image = Image.new("RGB", (100, 120), color=(255, 255, 255))
        face = Mock()
        scrfd = Mock()
        face.bbox = SimpleNamespace(
            upper_left=_point(0, 0),
            lower_right=_point(80, 90),
        )
        face.keypoints = SimpleNamespace(
            left_eye=_point(20.5, 30.0),
            right_eye=_point(60.0, 31.5),
            nose=_point(43.0, 51.0),
            left_mouth=_point(25.0, 75.5),
            right_mouth=_point(62.5, 76.0),
        )
        mock_scrfd.return_value = scrfd
        scrfd.get_face.return_value = face

        FaceHelper._get_face_landmark(
            weight_bytes=weight_bytes,
            image=image,
        )

        mock_scrfd.assert_called_once_with(
            weight_bytes=weight_bytes,
            device="cuda",
        )


class TestFaceHelperAlignmentFace:
    def test__alignment_face_returns_rgb_image_with_alignment_size(self) -> None:
        """基準ランドマークに揃った顔画像を112x112のRGB画像として返すこと。"""
        image = Image.new("L", FACE_ALIGNMENT_SIZE, color=128)
        face_image = FaceImage(
            image=image,
            landmarks=tuple(map(tuple, REFERENCE_FIVE_POINT_LANDMARKS)),
        )

        result = FaceHelper._alignment_face(face_image=face_image)

        assert result.size == FACE_ALIGNMENT_SIZE
        assert result.mode == "RGB"


class TestFaceHelperEstimateAffineMatrix:
    def test_estimate_affine_matrix_returns_matrix_mapping_source_to_target(self) -> None:
        """source_landmarksをtarget_landmarksへ写す2x3のアフィン変換行列を推定すること。"""
        source_landmarks = REFERENCE_FIVE_POINT_LANDMARKS * 2.0 + np.array(
            [10.0, 20.0],
            dtype=np.float32,
        )

        result = FaceHelper._estimate_affine_matrix(
            source_landmarks=source_landmarks,
            target_landmarks=REFERENCE_FIVE_POINT_LANDMARKS,
        )

        np.testing.assert_allclose(
            result,
            np.array(
                [
                    [0.5, 0.0, -5.0],
                    [0.0, 0.5, -10.0],
                ],
                dtype=np.float32,
            ),
            atol=1e-4,
        )

    @pytest.mark.parametrize(
        ("source_landmarks", "target_landmarks", "expected_message"),
        [
            (
                np.zeros((4, 2), dtype=np.float32),
                np.zeros((5, 2), dtype=np.float32),
                "source_landmarks must have shape (5, 2).",
            ),
            (
                np.zeros((5, 2), dtype=np.float32),
                np.zeros((5, 3), dtype=np.float32),
                "target_landmarks must have shape (5, 2).",
            ),
        ],
    )
    def test_estimate_affine_matrix_raises_value_error_when_landmarks_have_invalid_shape(
        self,
        source_landmarks,
        target_landmarks,
        expected_message,
    ) -> None:
        """ランドマーク配列のshapeが(5, 2)ではない場合はValueErrorを送出すること。"""
        with pytest.raises(ValueError) as exc_info:
            FaceHelper._estimate_affine_matrix(
                source_landmarks=source_landmarks,
                target_landmarks=target_landmarks,
            )
        assert str(exc_info.value) == expected_message


class TestFaceHelperGetEmbedding:
    @patch("app.helpers.face_helper.AdaFace")
    def test_get_embedding_passes_weight_bytes(self, mock_adaface) -> None:
        weight_bytes = b"adaface-weight"
        face_image = Image.new("RGB", FACE_ALIGNMENT_SIZE, color=(255, 255, 255))
        adaface = Mock()
        adaface.get_embedding.return_value = [0.1, 0.2, 0.3]
        mock_adaface.return_value = adaface

        result = FaceHelper._get_embedding(weight_bytes=weight_bytes, face_image=face_image)

        mock_adaface.assert_called_once_with(weight_bytes=weight_bytes, device="cuda")
        adaface.get_embedding.assert_called_once_with(image=face_image)
        assert result == [0.1, 0.2, 0.3]


class TestFaceHelperGetEmbeddingFromImage:
    @patch("app.helpers.face_helper.FaceHelper._get_embedding")
    @patch("app.helpers.face_helper.FaceHelper._alignment_face")
    @patch("app.helpers.face_helper.FaceHelper._get_face_landmark")
    def test_get_embedding_from_image_returns_embedding(
        self,
        mock__get_face_landmark,
        mock__alignment_face,
        mock_get_embedding,
    ) -> None:
        image = Image.new("RGB", (160, 120), color=(255, 0, 0))
        face_image = Mock()
        _alignment_face = Mock()
        embedding = [0.1] * 512
        ssm_params = SimpleNamespace(
            llm_weight_bucket="weights",
            scrfd_weight="scrfd/model.onnx",
            adaface_weight="adaface/model.ckpt",
        )
        s3_client = Mock()
        s3_client.get_object.side_effect = [b"scrfd-weight", b"adaface-weight"]
        mock__get_face_landmark.return_value = face_image
        mock__alignment_face.return_value = _alignment_face
        mock_get_embedding.return_value = embedding

        result = FaceHelper.get_embedding_from_image(
            image=image,
            s3_client=s3_client,
            ssm_params=ssm_params,
        )

        assert result == embedding
        assert s3_client.get_object.call_args_list[0].kwargs == {
            "bucket_name": "weights",
            "key": "scrfd/model.onnx",
        }
        assert s3_client.get_object.call_args_list[1].kwargs == {
            "bucket_name": "weights",
            "key": "adaface/model.ckpt",
        }
        mock__get_face_landmark.assert_called_once_with(
            weight_bytes=b"scrfd-weight",
            image=image,
        )
        mock__alignment_face.assert_called_once_with(face_image=face_image)
        mock_get_embedding.assert_called_once_with(
            weight_bytes=b"adaface-weight",
            face_image=_alignment_face,
        )
