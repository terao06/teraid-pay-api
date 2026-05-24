from math import ceil, floor
from pathlib import Path
from typing import NamedTuple

import numpy as np
from PIL import Image

from app.core.aws.s3_client import S3Client
from app.core.aws.ssm_manager import SsmClient
from app.ml.scrfd import Scrfd, ScrfdDevice
from app.ml.adaface import AdaFace


ML_ROOT = Path(__file__).resolve().parent
FACE_ALIGNMENT_SIZE = (112, 112)
REFERENCE_FIVE_POINT_LANDMARKS = np.array(
    [
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041],
    ],
    dtype=np.float32,
)


LandmarkPoint = tuple[float, float]
FaceLandmarks = tuple[LandmarkPoint, LandmarkPoint, LandmarkPoint, LandmarkPoint, LandmarkPoint]


class FaceImage(NamedTuple):
    image: Image.Image
    landmarks: FaceLandmarks


class FaceHelper:
    @classmethod
    def get_embedding_from_image(
        cls,
        image: Image.Image,
        s3_client: S3Client,
        ssm_params: SsmClient,
    ) -> list[float]:
        """画像から顔特徴量を抽出する。"""
        scrfd_weight_bytes = s3_client.get_object(
            bucket_name=ssm_params.llm_weight_bucket,
            key=ssm_params.scrfd_weight,
        )
        face_image = cls._get_face_landmark(weight_bytes=scrfd_weight_bytes, image=image)
        _alignment_face = cls._alignment_face(face_image=face_image)

        adaface_weight_bytes = s3_client.get_object(
            bucket_name=ssm_params.llm_weight_bucket,
            key=ssm_params.adaface_weight,
        )
        return cls._get_embedding(weight_bytes=adaface_weight_bytes, face_image=_alignment_face)

    @classmethod
    def _get_face_landmark(
        cls,
        weight_bytes: bytes,
        image: Image.Image,
    ) -> FaceImage:
        """画像から顔を検出し、顔画像と5点ランドマークを返す。

        Args:
            image: 顔検出の対象となる画像。

        Returns:
            検出した顔のバウンディングボックスで切り出した画像と、
            切り出し画像内の座標系に変換した5点ランドマーク。

        Raises:
            FaceNotFoundException: 顔を検出できなかった場合。
            SameFaceFoundException: 顔を複数検出した場合。
        """
        scrfd = Scrfd(
            weight_bytes=weight_bytes,
            device="cuda",
        )
        face = scrfd.get_face(image=image)
        bbox = face.bbox

        left = max(0, floor(bbox.upper_left.x))
        upper = max(0, floor(bbox.upper_left.y))
        right = min(image.width, ceil(bbox.lower_right.x))
        lower = min(image.height, ceil(bbox.lower_right.y))
        keypoints = face.keypoints

        landmarks: FaceLandmarks = (
            (keypoints.left_eye.x - left, keypoints.left_eye.y - upper),
            (keypoints.right_eye.x - left, keypoints.right_eye.y - upper),
            (keypoints.nose.x - left, keypoints.nose.y - upper),
            (keypoints.left_mouth.x - left, keypoints.left_mouth.y - upper),
            (keypoints.right_mouth.x - left, keypoints.right_mouth.y - upper),
        )

        return FaceImage(
            image=image.crop((left, upper, right, lower)),
            landmarks=landmarks,
        )

    @classmethod
    def _alignment_face(cls, face_image: FaceImage) -> Image.Image:
        """5点ランドマークを基準に顔画像を112x112へアライメントする。

        Args:
            face_image: _get_face_landmarkで取得した顔画像と5点ランドマーク。

        Returns:
            AdaFace/ArcFace系モデルに入力しやすい112x112のアライメント済み顔画像。
        """
        source_landmarks = np.asarray(face_image.landmarks, dtype=np.float32)
        affine_matrix = cls._estimate_affine_matrix(
            source_landmarks=source_landmarks,
            target_landmarks=REFERENCE_FIVE_POINT_LANDMARKS,
        )
        inverse_matrix = np.linalg.inv(
            np.vstack([affine_matrix, np.array([0.0, 0.0, 1.0], dtype=np.float32)])
        )
        coefficients = tuple(inverse_matrix[:2].reshape(6))

        return face_image.image.convert("RGB").transform(
            FACE_ALIGNMENT_SIZE,
            Image.Transform.AFFINE,
            coefficients,
            resample=Image.Resampling.BILINEAR,
        )

    @staticmethod
    def _estimate_affine_matrix(
        source_landmarks: np.ndarray,
        target_landmarks: np.ndarray,
    ) -> np.ndarray:
        """source_landmarksをtarget_landmarksへ写すアフィン変換行列を推定する。

        Args:
            source_landmarks: 変換前の5点ランドマーク。shapeは(5, 2)。
            target_landmarks: 変換後の基準5点ランドマーク。shapeは(5, 2)。

        Returns:
            Pillowのアフィン変換で使う2x3の変換行列。

        Raises:
            ValueError: ランドマークのshapeが(5, 2)ではない場合。
        """
        if source_landmarks.shape != (5, 2):
            raise ValueError("source_landmarks must have shape (5, 2).")
        if target_landmarks.shape != (5, 2):
            raise ValueError("target_landmarks must have shape (5, 2).")

        rows = []
        values = []
        for (source_x, source_y), (target_x, target_y) in zip(
            source_landmarks,
            target_landmarks,
        ):
            rows.append([source_x, source_y, 1.0, 0.0, 0.0, 0.0])
            rows.append([0.0, 0.0, 0.0, source_x, source_y, 1.0])
            values.extend([target_x, target_y])

        matrix = np.asarray(rows, dtype=np.float32)
        targets = np.asarray(values, dtype=np.float32)
        params, *_ = np.linalg.lstsq(matrix, targets, rcond=None)

        return np.asarray(
            [
                [params[0], params[1], params[2]],
                [params[3], params[4], params[5]],
            ],
            dtype=np.float32,
        )
    
    @classmethod
    def _get_embedding(cls, weight_bytes: bytes, face_image: Image.Image) -> list[float]:
        adaface = AdaFace(weight_bytes=weight_bytes, device="cuda")
        return adaface.get_embedding(image=face_image)
