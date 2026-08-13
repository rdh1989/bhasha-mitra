from types import SimpleNamespace

from ai.asr.models import ASRRequest
from ai.asr.service import ASRService


class FakeWhisperModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, audio_path, **kwargs):
        self.calls.append({"audio_path": audio_path, **kwargs})
        segments = [
            SimpleNamespace(start=0.0, end=1.0, text="hello"),
            SimpleNamespace(start=1.0, end=2.0, text="world"),
        ]
        info = SimpleNamespace(language="en", language_probability=0.98)
        return segments, info


class FakeModelManager:
    def __init__(self, model):
        self._model = model

    def get_default_model(self, category):
        assert category == "asr"
        return self._model


def test_model_manager_autoloads_registered_models_when_missing(monkeypatch):
    from pathlib import Path

    from ai.model_manager.manager import ModelManager

    manager = ModelManager()
    manager._registry.clear()
    manager._cache.clear()
    manager._registry.register(
        "asr",
        "small",
        Path("dummy-model"),
        "faster_whisper",
        "1.0",
    )

    fake_loaded = object()
    calls = []

    def fake_load_all():
        calls.append("load_all")
        manager._cache.add("asr:small", fake_loaded)

    monkeypatch.setattr(manager, "load_all", fake_load_all)

    loaded = manager.get_default_model("asr")

    assert loaded is fake_loaded
    assert calls == ["load_all"]


def test_transcribe_uses_balanced_decoding_settings(monkeypatch):
    fake_model = FakeWhisperModel()

    monkeypatch.setattr(
        "ai.asr.service.ModelManager",
        lambda: FakeModelManager(fake_model),
    )

    service = ASRService(adapter=None)
    result = service.transcribe(ASRRequest(audio_path="sample.wav"))

    assert result.transcript == "hello world"
    assert result.processing_time_seconds is not None
    assert result.processing_time_seconds >= 0

    assert len(fake_model.calls) == 1
    kwargs = fake_model.calls[0]
    assert kwargs["beam_size"] == 5
    assert kwargs["best_of"] == 5
    assert kwargs["vad_filter"] is True
    assert kwargs["vad_parameters"] == {"min_silence_duration_ms": 500}
    assert kwargs["condition_on_previous_text"] is False
    assert kwargs["without_timestamps"] is False
    assert kwargs["word_timestamps"] is False
