from __future__ import annotations

import math
from io import BytesIO
from collections import namedtuple
from typing import Iterable, Literal

import torch
import torch.nn as nn
from torch import Tensor
from torch.nn import (
    BatchNorm1d,
    BatchNorm2d,
    Conv2d,
    Dropout,
    Linear,
    MaxPool2d,
    Module,
    PReLU,
    Parameter,
    ReLU,
    Sequential,
    Sigmoid,
)

InputSize = tuple[int, int]
BackboneMode = Literal["ir", "ir_se"]
ModelName = Literal[
    "ir_18",
    "ir_34",
    "ir_50",
    "ir_101",
    "ir_152",
    "ir_200",
    "ir_se_50",
    "ir_se_101",
    "ir_se_152",
    "ir_se_200",
]
HeadType = Literal["adaface", "arcface", "cosface"]


class _LightningModelCheckpoint:
    """PyTorch Lightning ckpt の ModelCheckpoint メタデータ読み込み用ダミークラス。"""

    pass


_LightningModelCheckpoint.__module__ = "pytorch_lightning.callbacks.model_checkpoint"
_LightningModelCheckpoint.__qualname__ = "ModelCheckpoint"


def build_model(model_name: ModelName = "ir_50", input_size: InputSize = (112, 112)) -> "Backbone":
    """AdaFace のバックボーンモデルを生成する。

    Args:
        model_name: 生成するモデル名。
        input_size: 入力画像サイズ。

    Returns:
        指定された AdaFace バックボーン。

    Raises:
        ValueError: 未対応のモデル名が指定された場合。
    """
    if model_name == "ir_18":
        return IR_18(input_size=input_size)
    if model_name == "ir_34":
        return IR_34(input_size=input_size)
    if model_name == "ir_50":
        return IR_50(input_size=input_size)
    if model_name == "ir_101":
        return IR_101(input_size=input_size)
    if model_name == "ir_152":
        return IR_152(input_size=input_size)
    if model_name == "ir_200":
        return IR_200(input_size=input_size)
    if model_name == "ir_se_50":
        return IR_SE_50(input_size=input_size)
    if model_name == "ir_se_101":
        return IR_SE_101(input_size=input_size)
    if model_name == "ir_se_152":
        return IR_SE_152(input_size=input_size)
    if model_name == "ir_se_200":
        return IR_SE_200(input_size=input_size)
    raise ValueError(f"Unsupported AdaFace model name: {model_name}")


def build_head(
    head_type: HeadType,
    embedding_size: int,
    class_num: int,
    m: float,
    t_alpha: float = 1.0,
    h: float = 0.333,
    s: float = 64.0,
) -> Module:
    """顔認識学習用の分類ヘッドを生成する。

    Args:
        head_type: 生成するヘッド種別。
        embedding_size: 入力埋め込みの次元数。
        class_num: 分類クラス数。
        m: マージン値。
        t_alpha: AdaFace の移動平均更新率。
        h: AdaFace の品質適応係数。
        s: ロジットのスケール値。

    Returns:
        指定された分類ヘッド。

    Raises:
        ValueError: 未対応のヘッド種別が指定された場合。
    """
    if head_type == "adaface":
        return AdaFace(
            embedding_size=embedding_size,
            classnum=class_num,
            m=m,
            h=h,
            s=s,
            t_alpha=t_alpha,
        )
    if head_type == "arcface":
        return ArcFace(embedding_size=embedding_size, classnum=class_num, m=m, s=s)
    if head_type == "cosface":
        return CosFace(embedding_size=embedding_size, classnum=class_num, m=m, s=s)
    raise ValueError(f"Unsupported head type: {head_type}")


def initialize_weights(modules: Iterable[Module]) -> None:
    """畳み込み層、正規化層、全結合層の重みを初期化する。

    Args:
        modules: 初期化対象の PyTorch モジュール列。
    """
    for module in modules:
        if isinstance(module, nn.Conv2d):
            nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.BatchNorm2d):
            module.weight.data.fill_(1)
            module.bias.data.zero_()
        elif isinstance(module, nn.Linear):
            nn.init.kaiming_normal_(module.weight, mode="fan_out", nonlinearity="relu")
            if module.bias is not None:
                module.bias.data.zero_()


def l2_norm(input_tensor: Tensor, axis: int = 1) -> Tensor:
    """テンソルを指定軸に沿って L2 正規化する。

    Args:
        input_tensor: 正規化対象テンソル。
        axis: 正規化に使う軸。

    Returns:
        L2 正規化済みテンソル。
    """
    norm = torch.norm(input_tensor, 2, axis, True).clamp_min(1e-12)
    return torch.div(input_tensor, norm)


class Flatten(Module):
    def forward(self, input_tensor: Tensor) -> Tensor:
        """入力テンソルをバッチ次元を残して 2 次元に変換する。

        Args:
            input_tensor: 変換対象テンソル。

        Returns:
            2 次元に変換されたテンソル。
        """
        return input_tensor.view(input_tensor.size(0), -1)


class LinearBlock(Module):
    def __init__(
        self,
        in_c: int,
        out_c: int,
        kernel: tuple[int, int] = (1, 1),
        stride: tuple[int, int] = (1, 1),
        padding: tuple[int, int] = (0, 0),
        groups: int = 1,
    ) -> None:
        """畳み込みと BatchNorm を組み合わせた線形ブロックを初期化する。

        Args:
            in_c: 入力チャネル数。
            out_c: 出力チャネル数。
            kernel: カーネルサイズ。
            stride: ストライド。
            padding: パディング。
            groups: グループ畳み込み数。
        """
        super().__init__()
        self.conv = Conv2d(in_c, out_c, kernel, stride, padding, groups=groups, bias=False)
        self.bn = BatchNorm2d(out_c)

    def forward(self, x: Tensor) -> Tensor:
        """畳み込みと BatchNorm を適用する。

        Args:
            x: 入力特徴量。

        Returns:
            変換後の特徴量。
        """
        return self.bn(self.conv(x))


class GNAP(Module):
    """Global Norm-Aware Pooling from the AdaFace reference implementation."""

    def __init__(self, in_c: int) -> None:
        """Global Norm-Aware Pooling を初期化する。

        Args:
            in_c: 入力チャネル数。
        """
        super().__init__()
        self.bn1 = BatchNorm2d(in_c, affine=False)
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.bn2 = BatchNorm1d(in_c, affine=False)

    def forward(self, x: Tensor) -> Tensor:
        """特徴量のノルムを補正してグローバルプーリングする。

        Args:
            x: 入力特徴量。

        Returns:
            プーリング後の特徴量。
        """
        x = self.bn1(x)
        x_norm = torch.norm(x, 2, 1, True).clamp_min(1e-12)
        x_norm_mean = torch.mean(x_norm)
        x = x * (x_norm_mean / x_norm)
        x = self.pool(x)
        return self.bn2(x.view(x.shape[0], -1))


class GDC(Module):
    """Global Depthwise Convolution head used by some face backbones."""

    def __init__(self, in_c: int, embedding_size: int) -> None:
        """Global Depthwise Convolution ヘッドを初期化する。

        Args:
            in_c: 入力チャネル数。
            embedding_size: 出力埋め込みの次元数。
        """
        super().__init__()
        self.conv_6_dw = LinearBlock(
            in_c,
            in_c,
            groups=in_c,
            kernel=(7, 7),
            stride=(1, 1),
            padding=(0, 0),
        )
        self.conv_6_flatten = Flatten()
        self.linear = Linear(in_c, embedding_size, bias=False)
        self.bn = BatchNorm1d(embedding_size, affine=False)

    def forward(self, x: Tensor) -> Tensor:
        """Depthwise Convolution で埋め込みを生成する。

        Args:
            x: 入力特徴量。

        Returns:
            生成された埋め込み。
        """
        x = self.conv_6_dw(x)
        x = self.conv_6_flatten(x)
        return self.bn(self.linear(x))


class SEModule(Module):
    def __init__(self, channels: int, reduction: int) -> None:
        """Squeeze-and-Excitation モジュールを初期化する。

        Args:
            channels: 入力チャネル数。
            reduction: チャネル圧縮率。
        """
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = Conv2d(channels, channels // reduction, kernel_size=1, padding=0, bias=False)
        nn.init.xavier_uniform_(self.fc1.weight.data)
        self.relu = ReLU(inplace=True)
        self.fc2 = Conv2d(channels // reduction, channels, kernel_size=1, padding=0, bias=False)
        self.sigmoid = Sigmoid()

    def forward(self, x: Tensor) -> Tensor:
        """チャネルごとの重要度で特徴量を再重み付けする。

        Args:
            x: 入力特徴量。

        Returns:
            再重み付け後の特徴量。
        """
        module_input = x
        x = self.avg_pool(x)
        x = self.relu(self.fc1(x))
        x = self.sigmoid(self.fc2(x))
        return module_input * x


class BasicBlockIR(Module):
    def __init__(self, in_channel: int, depth: int, stride: int) -> None:
        """IR 系の基本残差ブロックを初期化する。

        Args:
            in_channel: 入力チャネル数。
            depth: 出力チャネル数。
            stride: ストライド。
        """
        super().__init__()
        if in_channel == depth:
            self.shortcut_layer = MaxPool2d(1, stride)
        else:
            self.shortcut_layer = Sequential(
                Conv2d(in_channel, depth, (1, 1), stride, bias=False),
                BatchNorm2d(depth),
            )
        self.res_layer = Sequential(
            BatchNorm2d(in_channel),
            Conv2d(in_channel, depth, (3, 3), (1, 1), 1, bias=False),
            BatchNorm2d(depth),
            PReLU(depth),
            Conv2d(depth, depth, (3, 3), stride, 1, bias=False),
            BatchNorm2d(depth),
        )

    def forward(self, x: Tensor) -> Tensor:
        """残差経路とショートカット経路を加算する。

        Args:
            x: 入力特徴量。

        Returns:
            残差ブロックの出力特徴量。
        """
        return self.res_layer(x) + self.shortcut_layer(x)


class BottleneckIR(Module):
    def __init__(self, in_channel: int, depth: int, stride: int) -> None:
        """Bottleneck 形式の IR 残差ブロックを初期化する。

        Args:
            in_channel: 入力チャネル数。
            depth: 出力チャネル数。
            stride: ストライド。
        """
        super().__init__()
        reduction_channel = depth // 4
        if in_channel == depth:
            self.shortcut_layer = MaxPool2d(1, stride)
        else:
            self.shortcut_layer = Sequential(
                Conv2d(in_channel, depth, (1, 1), stride, bias=False),
                BatchNorm2d(depth),
            )
        self.res_layer = Sequential(
            BatchNorm2d(in_channel),
            Conv2d(in_channel, reduction_channel, (1, 1), (1, 1), 0, bias=False),
            BatchNorm2d(reduction_channel),
            PReLU(reduction_channel),
            Conv2d(reduction_channel, reduction_channel, (3, 3), (1, 1), 1, bias=False),
            BatchNorm2d(reduction_channel),
            PReLU(reduction_channel),
            Conv2d(reduction_channel, depth, (1, 1), stride, 0, bias=False),
            BatchNorm2d(depth),
        )

    def forward(self, x: Tensor) -> Tensor:
        """Bottleneck 残差経路とショートカット経路を加算する。

        Args:
            x: 入力特徴量。

        Returns:
            残差ブロックの出力特徴量。
        """
        return self.res_layer(x) + self.shortcut_layer(x)


class BasicBlockIRSE(BasicBlockIR):
    def __init__(self, in_channel: int, depth: int, stride: int) -> None:
        """SE 付き IR 基本残差ブロックを初期化する。

        Args:
            in_channel: 入力チャネル数。
            depth: 出力チャネル数。
            stride: ストライド。
        """
        super().__init__(in_channel, depth, stride)
        self.res_layer.add_module("se_block", SEModule(depth, 16))


class BottleneckIRSE(BottleneckIR):
    def __init__(self, in_channel: int, depth: int, stride: int) -> None:
        """SE 付き Bottleneck IR 残差ブロックを初期化する。

        Args:
            in_channel: 入力チャネル数。
            depth: 出力チャネル数。
            stride: ストライド。
        """
        super().__init__(in_channel, depth, stride)
        self.res_layer.add_module("se_block", SEModule(depth, 16))


class Bottleneck(namedtuple("Block", ["in_channel", "depth", "stride"])):
    pass


def get_block(in_channel: int, depth: int, num_units: int, stride: int = 2) -> list[Bottleneck]:
    """同じステージに属する Bottleneck 定義を生成する。

    Args:
        in_channel: ステージ先頭の入力チャネル数。
        depth: ステージの出力チャネル数。
        num_units: ステージ内のブロック数。
        stride: ステージ先頭のストライド。

    Returns:
        Bottleneck 定義のリスト。
    """
    return [Bottleneck(in_channel, depth, stride)] + [
        Bottleneck(depth, depth, 1) for _ in range(num_units - 1)
    ]


def get_blocks(num_layers: int) -> list[list[Bottleneck]]:
    """層数に対応する AdaFace バックボーンのブロック構成を返す。

    Args:
        num_layers: バックボーンの層数。

    Returns:
        ステージごとの Bottleneck 定義。

    Raises:
        ValueError: 未対応の層数が指定された場合。
    """
    if num_layers == 18:
        return [
            get_block(in_channel=64, depth=64, num_units=2),
            get_block(in_channel=64, depth=128, num_units=2),
            get_block(in_channel=128, depth=256, num_units=2),
            get_block(in_channel=256, depth=512, num_units=2),
        ]
    if num_layers == 34:
        return [
            get_block(in_channel=64, depth=64, num_units=3),
            get_block(in_channel=64, depth=128, num_units=4),
            get_block(in_channel=128, depth=256, num_units=6),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    if num_layers == 50:
        return [
            get_block(in_channel=64, depth=64, num_units=3),
            get_block(in_channel=64, depth=128, num_units=4),
            get_block(in_channel=128, depth=256, num_units=14),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    if num_layers == 100:
        return [
            get_block(in_channel=64, depth=64, num_units=3),
            get_block(in_channel=64, depth=128, num_units=13),
            get_block(in_channel=128, depth=256, num_units=30),
            get_block(in_channel=256, depth=512, num_units=3),
        ]
    if num_layers == 152:
        return [
            get_block(in_channel=64, depth=256, num_units=3),
            get_block(in_channel=256, depth=512, num_units=8),
            get_block(in_channel=512, depth=1024, num_units=36),
            get_block(in_channel=1024, depth=2048, num_units=3),
        ]
    if num_layers == 200:
        return [
            get_block(in_channel=64, depth=256, num_units=3),
            get_block(in_channel=256, depth=512, num_units=24),
            get_block(in_channel=512, depth=1024, num_units=36),
            get_block(in_channel=1024, depth=2048, num_units=3),
        ]
    raise ValueError(f"Unsupported AdaFace depth: {num_layers}")


class Backbone(Module):
    def __init__(self, input_size: InputSize, num_layers: int, mode: BackboneMode = "ir") -> None:
        """AdaFace の IR/IR-SE バックボーンを初期化する。

        Args:
            input_size: 入力画像サイズ。
            num_layers: バックボーンの層数。
            mode: バックボーン種別。

        Raises:
            ValueError: 未対応の入力サイズ、層数、または種別が指定された場合。
        """
        super().__init__()
        if input_size not in [(112, 112), (224, 224)]:
            raise ValueError("input_size must be (112, 112) or (224, 224)")
        if num_layers not in [18, 34, 50, 100, 152, 200]:
            raise ValueError("num_layers must be one of 18, 34, 50, 100, 152, 200")
        if mode not in ["ir", "ir_se"]:
            raise ValueError("mode must be 'ir' or 'ir_se'")

        self.input_size = input_size
        self.num_layers = num_layers
        self.mode = mode
        self.input_layer = Sequential(
            Conv2d(3, 64, (3, 3), 1, 1, bias=False),
            BatchNorm2d(64),
            PReLU(64),
        )

        if num_layers <= 100:
            unit_module: type[Module] = BasicBlockIR if mode == "ir" else BasicBlockIRSE
            output_channel = 512
        else:
            unit_module = BottleneckIR if mode == "ir" else BottleneckIRSE
            output_channel = 2048

        output_spatial = 7 if input_size == (112, 112) else 14
        self.output_layer = Sequential(
            BatchNorm2d(output_channel),
            Dropout(0.4),
            Flatten(),
            Linear(output_channel * output_spatial * output_spatial, 512),
            BatchNorm1d(512, affine=False),
        )

        modules = []
        for block in get_blocks(num_layers):
            for bottleneck in block:
                modules.append(unit_module(bottleneck.in_channel, bottleneck.depth, bottleneck.stride))
        self.body = Sequential(*modules)
        initialize_weights(self.modules())

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        """顔画像テンソルから正規化埋め込みと埋め込みノルムを生成する。

        Args:
            x: BGR 正規化済みの入力テンソル。

        Returns:
            正規化済み埋め込みと正規化前ノルム。
        """
        x = self.input_layer(x)
        x = self.body(x)
        x = self.output_layer(x)
        norm = torch.norm(x, 2, 1, True).clamp_min(1e-12)
        output = torch.div(x, norm)
        return output, norm


class AdaFace(Module):
    def __init__(
        self,
        embedding_size: int = 512,
        classnum: int = 70722,
        m: float = 0.4,
        h: float = 0.333,
        s: float = 64.0,
        t_alpha: float = 1.0,
    ) -> None:
        """AdaFace 分類ヘッドを初期化する。

        Args:
            embedding_size: 入力埋め込みの次元数。
            classnum: 分類クラス数。
            m: 基本マージン値。
            h: ノルムに基づく品質適応係数。
            s: ロジットのスケール値。
            t_alpha: バッチ統計の移動平均更新率。
        """
        super().__init__()
        self.classnum = classnum
        self.kernel = Parameter(torch.Tensor(embedding_size, classnum))
        self.kernel.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)
        self.m = m
        self.eps = 1e-3
        self.h = h
        self.s = s
        self.t_alpha = t_alpha
        self.register_buffer("batch_mean", torch.ones(1) * 20)
        self.register_buffer("batch_std", torch.ones(1) * 100)

    def forward(self, embeddings: Tensor, norms: Tensor, label: Tensor) -> Tensor:
        """埋め込み品質に応じた AdaFace マージンを適用してロジットを返す。

        Args:
            embeddings: L2 正規化済みの顔埋め込み。
            norms: 正規化前の埋め込みノルム。
            label: 正解クラスラベル。

        Returns:
            AdaFace マージン適用後の分類ロジット。
        """
        kernel_norm = l2_norm(self.kernel, axis=0)
        cosine = torch.mm(embeddings, kernel_norm).clamp(-1 + self.eps, 1 - self.eps)
        safe_norms = torch.clip(norms, min=0.001, max=100).clone().detach()

        with torch.no_grad():
            mean = safe_norms.mean().detach()
            std = safe_norms.std(unbiased=False).detach()
            self.batch_mean.mul_(1 - self.t_alpha).add_(mean * self.t_alpha)
            self.batch_std.mul_(1 - self.t_alpha).add_(std * self.t_alpha)

        margin_scaler = (safe_norms - self.batch_mean) / (self.batch_std + self.eps)
        margin_scaler = torch.clip(margin_scaler * self.h, -1, 1)

        m_arc = torch.zeros(label.size(0), cosine.size(1), device=cosine.device)
        m_arc.scatter_(1, label.reshape(-1, 1), 1.0)
        g_angular = self.m * margin_scaler * -1
        theta = cosine.acos()
        theta_m = torch.clip(theta + (m_arc * g_angular), min=self.eps, max=math.pi - self.eps)
        cosine = theta_m.cos()

        m_cos = torch.zeros(label.size(0), cosine.size(1), device=cosine.device)
        m_cos.scatter_(1, label.reshape(-1, 1), 1.0)
        g_add = self.m + (self.m * margin_scaler)
        cosine = cosine - (m_cos * g_add)
        return cosine * self.s


class CosFace(Module):
    def __init__(self, embedding_size: int = 512, classnum: int = 51332, s: float = 64.0, m: float = 0.4):
        """CosFace 分類ヘッドを初期化する。

        Args:
            embedding_size: 入力埋め込みの次元数。
            classnum: 分類クラス数。
            s: ロジットのスケール値。
            m: コサインマージン値。
        """
        super().__init__()
        self.classnum = classnum
        self.kernel = Parameter(torch.Tensor(embedding_size, classnum))
        self.kernel.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)
        self.m = m
        self.s = s
        self.eps = 1e-4

    def forward(self, embeddings: Tensor, norms: Tensor, label: Tensor) -> Tensor:
        """CosFace のコサインマージンを適用してロジットを返す。

        Args:
            embeddings: L2 正規化済みの顔埋め込み。
            norms: AdaFace とインターフェースを合わせるための未使用ノルム。
            label: 正解クラスラベル。

        Returns:
            CosFace マージン適用後の分類ロジット。
        """
        del norms
        kernel_norm = l2_norm(self.kernel, axis=0)
        cosine = torch.mm(embeddings, kernel_norm).clamp(-1 + self.eps, 1 - self.eps)
        m_hot = torch.zeros(label.size(0), cosine.size(1), device=cosine.device)
        m_hot.scatter_(1, label.reshape(-1, 1), self.m)
        return (cosine - m_hot) * self.s


class ArcFace(Module):
    def __init__(self, embedding_size: int = 512, classnum: int = 51332, s: float = 64.0, m: float = 0.5):
        """ArcFace 分類ヘッドを初期化する。

        Args:
            embedding_size: 入力埋め込みの次元数。
            classnum: 分類クラス数。
            s: ロジットのスケール値。
            m: 角度マージン値。
        """
        super().__init__()
        self.classnum = classnum
        self.kernel = Parameter(torch.Tensor(embedding_size, classnum))
        self.kernel.data.uniform_(-1, 1).renorm_(2, 1, 1e-5).mul_(1e5)
        self.m = m
        self.s = s
        self.eps = 1e-4

    def forward(self, embeddings: Tensor, norms: Tensor, label: Tensor) -> Tensor:
        """ArcFace の角度マージンを適用してロジットを返す。

        Args:
            embeddings: L2 正規化済みの顔埋め込み。
            norms: AdaFace とインターフェースを合わせるための未使用ノルム。
            label: 正解クラスラベル。

        Returns:
            ArcFace マージン適用後の分類ロジット。
        """
        del norms
        kernel_norm = l2_norm(self.kernel, axis=0)
        cosine = torch.mm(embeddings, kernel_norm).clamp(-1 + self.eps, 1 - self.eps)
        m_hot = torch.zeros(label.size(0), cosine.size(1), device=cosine.device)
        m_hot.scatter_(1, label.reshape(-1, 1), self.m)
        theta = cosine.acos()
        theta_m = torch.clip(theta + m_hot, min=self.eps, max=math.pi - self.eps)
        return theta_m.cos() * self.s


def IR_18(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-18 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-18 バックボーン。
    """
    return Backbone(input_size, 18, "ir")


def IR_34(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-34 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-34 バックボーン。
    """
    return Backbone(input_size, 34, "ir")


def IR_50(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-50 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-50 バックボーン。
    """
    return Backbone(input_size, 50, "ir")


def IR_101(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-101 相当のバックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-101 相当のバックボーン。
    """
    return Backbone(input_size, 100, "ir")


def IR_152(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-152 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-152 バックボーン。
    """
    return Backbone(input_size, 152, "ir")


def IR_200(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-200 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-200 バックボーン。
    """
    return Backbone(input_size, 200, "ir")


def IR_SE_50(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-SE-50 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-SE-50 バックボーン。
    """
    return Backbone(input_size, 50, "ir_se")


def IR_SE_101(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-SE-101 相当のバックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-SE-101 相当のバックボーン。
    """
    return Backbone(input_size, 100, "ir_se")


def IR_SE_152(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-SE-152 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-SE-152 バックボーン。
    """
    return Backbone(input_size, 152, "ir_se")


def IR_SE_200(input_size: InputSize = (112, 112)) -> Backbone:
    """IR-SE-200 バックボーンを生成する。

    Args:
        input_size: 入力画像サイズ。

    Returns:
        IR-SE-200 バックボーン。
    """
    return Backbone(input_size, 200, "ir_se")


def load_pretrained_model(
    weight_bytes: BytesIO,
    architecture: ModelName = "ir_50",
    map_location: torch.device = torch.device("cpu"),
) -> Backbone:
    """学習済み重みを読み込んだ AdaFace バックボーンを生成する。

    Args:
        weight_bytes: 重みデータの BytesIO。
        architecture: 生成するバックボーン名。
        map_location: 重みを読み込むデバイス。

    Returns:
        評価モードに設定された AdaFace バックボーン。
    """
    model = build_model(architecture)
    weight_bytes.seek(0)
    checkpoint = _load_checkpoint(weight_bytes, map_location=map_location)
    state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model_state_dict = {
        key.removeprefix("model."): value
        for key, value in state_dict.items()
        if not key.startswith("head.") and not key.startswith("loss.")
    }
    model.load_state_dict(model_state_dict)
    model.eval()
    return model


def _load_checkpoint(
    weight_bytes: BytesIO,
    map_location: torch.device = torch.device("cpu"),
) -> object:
    """AdaFace の PyTorch Lightning ckpt を state_dict 抽出用に読み込む。

    Args:
        weight_bytes: 重みデータの BytesIO。
        map_location: 重みを読み込むデバイス。

    Returns:
        読み込んだ checkpoint オブジェクト。
    """
    with torch.serialization.safe_globals([_LightningModelCheckpoint]):
        return torch.load(weight_bytes, map_location=map_location, weights_only=True)
