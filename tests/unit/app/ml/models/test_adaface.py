import pytest

torch = pytest.importorskip("torch")

from app.ml.models.adaface import AdaFace, ArcFace, CosFace, build_head, build_model


class TestAdaFaceBackbone:
    def test_build_ir18_outputs_normalized_embedding_and_norm(self):
        model = build_model("ir_18")
        model.eval()

        with torch.no_grad():
            embedding, norm = model(torch.randn(2, 3, 112, 112))

        assert embedding.shape == (2, 512)
        assert norm.shape == (2, 1)
        assert torch.allclose(torch.norm(embedding, 2, 1), torch.ones(2), atol=1e-5)

    def test_build_model_rejects_unknown_name(self):
        with pytest.raises(ValueError):
            build_model("unknown")  # type: ignore[arg-type]


class TestAdaFaceHeads:
    @pytest.mark.parametrize(
        ("head_type", "expected_type"),
        [
            ("adaface", AdaFace),
            ("arcface", ArcFace),
            ("cosface", CosFace),
        ],
    )
    def test_build_head(self, head_type, expected_type):
        head = build_head(head_type, embedding_size=4, class_num=3, m=0.4)

        assert isinstance(head, expected_type)

    def test_adaface_forward_returns_class_logits(self):
        head = AdaFace(embedding_size=4, classnum=3, t_alpha=0.5)
        embeddings = torch.nn.functional.normalize(torch.randn(2, 4), dim=1)
        norms = torch.tensor([[20.0], [30.0]])
        labels = torch.tensor([0, 2])

        logits = head(embeddings, norms, labels)

        assert logits.shape == (2, 3)
        assert torch.isfinite(logits).all()
