import sys
import types
from pathlib import Path

import ai.model_manager.loader as loader_module
from ai.model_manager.loader import ModelLoader


class FakeRegistry:
    def __init__(self, metadata):
        self._metadata = metadata

    def exists(self, category, model):
        return True

    def get(self, category, model):
        return self._metadata


def test_nllb_loader_uses_nllb_model_classes(monkeypatch, tmp_path):
    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True):
            assert path == str(tmp_path)
            return object()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True, **kwargs):
            assert path == str(tmp_path)
            return object()

    transformers_module = types.ModuleType("transformers")
    transformers_module.NllbTokenizer = FakeTokenizer
    transformers_module.NllbForConditionalGeneration = FakeModel

    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    loader = ModelLoader(
        FakeRegistry(
            {
                "provider": "nllb",
                "path": str(tmp_path),
            }
        )
    )

    result = loader.load("translation", "NLLB-600M")

    assert result["model"] is not None
    assert result["tokenizer"] is not None


def test_nllb_loader_resolves_manifest_relative_path(monkeypatch, tmp_path):
    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True):
            return object()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True, **kwargs):
            return object()

    transformers_module = types.ModuleType("transformers")
    transformers_module.NllbTokenizer = FakeTokenizer
    transformers_module.NllbForConditionalGeneration = FakeModel

    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    repo_root = tmp_path / "repo"
    loader_path = repo_root / "ai" / "model_manager" / "loader.py"
    loader_path.parent.mkdir(parents=True, exist_ok=True)
    model_dir = tmp_path / "models" / "translation" / "NLLB-600M"
    model_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(loader_module, "__file__", str(loader_path))

    loader = ModelLoader(
        FakeRegistry(
            {
                "provider": "nllb",
                "path": "../models/translation/NLLB-600M",
            }
        )
    )

    result = loader.load("translation", "NLLB-600M")

    assert result["model"] is not None
    assert result["tokenizer"] is not None


def test_nllb_loader_falls_back_to_pytorch_checkpoint(monkeypatch, tmp_path):
    captured = {}

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True):
            return object()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, path, local_files_only=True, **kwargs):
            captured.update(kwargs)
            return object()

    transformers_module = types.ModuleType("transformers")
    transformers_module.AutoTokenizer = FakeTokenizer
    transformers_module.AutoModelForSeq2SeqLM = FakeModel

    monkeypatch.setitem(sys.modules, "transformers", transformers_module)

    model_dir = tmp_path / "NLLB-600M"
    model_dir.mkdir(parents=True, exist_ok=True)
    for file_name in [
        "config.json",
        "generation_config.json",
        "pytorch_model.bin",
        "tokenizer_config.json",
    ]:
        (model_dir / file_name).write_text("{}", encoding="utf-8")

    loader = ModelLoader(
        FakeRegistry(
            {
                "provider": "nllb",
                "path": str(model_dir),
            }
        )
    )

    result = loader.load("translation", "NLLB-600M")

    assert result["model"] is not None
    assert result["tokenizer"] is not None
    assert captured.get("use_safetensors") is False
