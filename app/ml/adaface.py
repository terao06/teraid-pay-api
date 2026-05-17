from pathlib import Path

import numpy as np
import torch
from PIL import Image

from app.ml.models.adaface import ModelName, load_pretrained_model


ML_ROOT = Path(__file__).resolve().parent


class AdaFace:
    def __init__(
        self,
        weight_bytes: bytes,
        architecture: ModelName = "ir_50",
        device: str | torch.device = "cpu",
    ) -> None:
        """AdaFace ラッパーを初期化する。

        Args:
            weight_bytes: AdaFace の重みデータ。
            architecture: 使用する AdaFace バックボーン名。
            device: 推論に使用するデバイス。
        """
        self.weight_bytes = weight_bytes
        self.architecture = architecture
        self.device = torch.device(device)
        self._model = None

    def get_embedding(self, image: Image.Image) -> list[float]:
        """アライメント済み顔画像から AdaFace 埋め込みを生成する。

        Args:
            image: 112x112 にアライメント済みの RGB 顔画像。

        Returns:
            L2 正規化済みの 512 次元埋め込み。
        """
        if self._model is None:
            self._model = load_pretrained_model(
                weight_bytes=self.weight_bytes,
                architecture=self.architecture,
                map_location=self.device,
            ).to(self.device)

        input_tensor = self._to_bgr_input(image).to(self.device)
        with torch.inference_mode():
            embedding, _ = self._model(input_tensor)

        return embedding.squeeze(0).cpu().tolist()

    @staticmethod
    def _to_bgr_input(image: Image.Image) -> torch.Tensor:
        """位置合わせ済み顔画像を AdaFace 用の BGR 入力テンソルに変換する。

        Args:
            image: 112x112 にアライメント済みの RGB 顔画像。

        Returns:
            BGR 順に並べ替え、平均 0.5、標準偏差 0.5 で正規化した入力テンソル。
        """
        np_img = np.array(image.convert("RGB"))
        bgr_img = ((np_img[:, :, ::-1].astype(np.float32) / 255.0) - 0.5) / 0.5
        return torch.from_numpy(bgr_img.transpose(2, 0, 1)).unsqueeze(0).float()
