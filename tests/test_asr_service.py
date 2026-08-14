from types import SimpleNamespace

from ai.asr.models import ASRRequest
from ai.asr.service import ASRService


class FakeWhisperModel:
    def __init__(self, with_words=True):
        self.calls = []
        self._with_words = with_words

    def transcribe(self, audio_path, **kwargs):
        self.calls.append({"audio_path": audio_path, **kwargs})

        words_hello = (
            [
                SimpleNamespace(word="hello", start=0.0, end=1.0, probability=0.9),
            ]
            if self._with_words
            else None
        )
        words_world = (
            [
                SimpleNamespace(word="world", start=1.0, end=2.0, probability=0.8),
            ]
            if self._with_words
            else None
        )

        segments = [
            SimpleNamespace(start=0.0, end=1.0, text="hello", words=words_hello),
            SimpleNamespace(start=1.0, end=2.0, text="world", words=words_world),
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
    assert kwargs["word_timestamps"] is True


def test_transcribe_extracts_word_level_timestamps(monkeypatch):
    """Test 1: normal sentence with word timestamps."""

    fake_model = FakeWhisperModel(with_words=True)

    monkeypatch.setattr(
        "ai.asr.service.ModelManager",
        lambda: FakeModelManager(fake_model),
    )

    service = ASRService(adapter=None)
    result = service.transcribe(ASRRequest(audio_path="sample.wav"))

    assert len(result.segments) == 2

    first_words = result.segments[0].words
    assert len(first_words) == 1
    assert first_words[0].word == "hello"
    assert first_words[0].start == 0.0
    assert first_words[0].end == 1.0
    assert first_words[0].confidence == 0.9

    second_words = result.segments[1].words
    assert second_words[0].word == "world"
    assert second_words[0].confidence == 0.8


def test_transcribe_falls_back_gracefully_without_word_timestamps(monkeypatch):
    """Test 4: missing word timestamps -> segment-level fallback."""

    fake_model = FakeWhisperModel(with_words=False)

    monkeypatch.setattr(
        "ai.asr.service.ModelManager",
        lambda: FakeModelManager(fake_model),
    )

    service = ASRService(adapter=None)
    result = service.transcribe(ASRRequest(audio_path="sample.wav"))

    assert result.transcript == "hello world"
    assert len(result.segments) == 2
    assert result.segments[0].words == []
    assert result.segments[1].words == []
    # Segment-level timing must remain intact even without word timing.
    assert result.segments[0].start == 0.0
    assert result.segments[0].end == 1.0
