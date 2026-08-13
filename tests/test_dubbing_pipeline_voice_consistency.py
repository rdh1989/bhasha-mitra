from __future__ import annotations

import wave
from pathlib import Path

from ai.pipeline.contracts import VideoDubbingRequest
from ai.pipeline.dubbing_pipeline import DubbingPipeline
from ai.tts.models import SpeechResult


class _FakeTTSService:
    def __init__(self, duration_seconds: float = 0.5) -> None:
        self.calls = []
        self._duration_seconds = duration_seconds

    def synthesize(self, request):
        self.calls.append(request)

        sample_rate = 22050
        frame_count = int(self._duration_seconds * sample_rate)

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(request.output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)

        return SpeechResult(
            audio_path=request.output_path,
            language=request.language,
            voice=request.voice,
            sample_rate=sample_rate,
            duration=self._duration_seconds,
        )


class _VariableFakeTTSService:
    def __init__(self, durations: list[float]) -> None:
        self.calls = []
        self._durations = durations

    def synthesize(self, request):
        self.calls.append(request)

        sample_rate = 22050
        index = min(len(self.calls) - 1, len(self._durations) - 1)
        duration_seconds = self._durations[index]
        frame_count = int(duration_seconds * sample_rate)

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        with wave.open(str(request.output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)

        return SpeechResult(
            audio_path=request.output_path,
            language=request.language,
            voice=request.voice,
            sample_rate=sample_rate,
            duration=duration_seconds,
        )


class _FakeModelManager:
    def get_default_metadata(self, category: str):
        assert category == "tts"
        return {
            "model": "mr_IN-google-medium",
        }


def test_dubbing_pipeline_ignores_request_voice_and_uses_configured_voice(
    monkeypatch,
    tmp_path: Path,
) -> None:
    translation_path = tmp_path / "translation.json"
    translation_path.write_text(
        """
{
  "segments": [
    {"id": 1, "start": 0.0, "end": 1.0, "translated_text": "नमस्कार"},
    {"id": 2, "start": 1.0, "end": 2.0, "translated_text": "ही एक चाचणी आहे"}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    tts_service = _FakeTTSService(duration_seconds=0.4)
    pipeline = DubbingPipeline(tts_service=tts_service)

    monkeypatch.setattr(
        pipeline,
        "_model_manager",
        _FakeModelManager(),
    )

    output_path = tmp_path / "dubbed_audio.wav"

    result = pipeline.execute(
        VideoDubbingRequest(
            translated_text_path=translation_path,
            language="mr",
            voice="some-other-voice",
            output_path=output_path,
        )
    )

    assert output_path.exists()
    assert result.voice == "mr_IN-google-medium"

    assert len(tts_service.calls) == 2
    assert all(
        call.voice == "mr_IN-google-medium"
        for call in tts_service.calls
    )


def test_dubbing_pipeline_avoids_aggressive_resample_for_overlong_segments(
    monkeypatch,
    tmp_path: Path,
) -> None:
    translation_path = tmp_path / "translation.json"
    translation_path.write_text(
        """
{
  "segments": [
    {"id": 1, "start": 0.0, "end": 1.0, "translated_text": "हा मजकूर मोठा आहे"}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    # Force TTS duration to be much longer than target timeline.
    tts_service = _FakeTTSService(duration_seconds=3.0)
    pipeline = DubbingPipeline(tts_service=tts_service)

    monkeypatch.setattr(
        pipeline,
        "_model_manager",
        _FakeModelManager(),
    )

    resize_called = {"value": False}

    original_resize = pipeline._resize_audio

    def wrapped_resize(*args, **kwargs):
        resize_called["value"] = True
        return original_resize(*args, **kwargs)

    monkeypatch.setattr(
        pipeline,
        "_resize_audio",
        wrapped_resize,
    )

    output_path = tmp_path / "dubbed_audio.wav"

    pipeline.execute(
        VideoDubbingRequest(
            translated_text_path=translation_path,
            language="mr",
            voice="ignored",
            output_path=output_path,
        )
    )

    assert output_path.exists()
    assert resize_called["value"] is False


def test_dubbing_pipeline_splits_long_segment_for_tts(monkeypatch, tmp_path: Path) -> None:
        translation_path = tmp_path / "translation.json"
        translation_path.write_text(
                """
{
    "segments": [
        {
            "id": 1,
            "start": 68.58,
            "end": 87.34,
            "translated_text": "ही एक मोठी वाक्यरचना आहे, जी नैसर्गिक थांबे घेते. पुढील भाग अर्थपूर्ण आहे, आणि बोलण्याचा वेग स्थिर ठेवतो. शेवट स्पष्ट आणि पूर्ण असावा."
        }
    ]
}
""".strip(),
                encoding="utf-8",
        )

        tts_service = _FakeTTSService(duration_seconds=1.0)
        pipeline = DubbingPipeline(tts_service=tts_service)

        monkeypatch.setattr(
                pipeline,
                "_model_manager",
                _FakeModelManager(),
        )

        output_path = tmp_path / "dubbed_audio.wav"

        pipeline.execute(
                VideoDubbingRequest(
                        translated_text_path=translation_path,
                        language="mr",
                        voice="ignored",
                        output_path=output_path,
                )
        )

        assert output_path.exists()
        assert len(tts_service.calls) >= 2


def test_dubbing_pipeline_regenerates_for_significant_overflow(
        monkeypatch,
        tmp_path: Path,
) -> None:
        translation_path = tmp_path / "translation.json"
        translation_path.write_text(
                """
{
    "segments": [
        {
            "id": 1,
            "start": 249.54,
            "end": 265.42,
            "translated_text": "हा एक खूप लांब अनुवादित भाग आहे, ज्यामध्ये अनेक उपवाक्ये आहेत, आणि त्यामुळे पुनर्विभाजन आवश्यक आहे, जेणेकरून शेवट कापला जाणार नाही."
        }
    ]
}
""".strip(),
                encoding="utf-8",
        )

        # First synthesis overflows heavily; subsequent synthesized chunks fit.
        tts_service = _VariableFakeTTSService([20.0, 4.0, 4.0, 4.0])
        pipeline = DubbingPipeline(tts_service=tts_service)

        monkeypatch.setattr(
                pipeline,
                "_model_manager",
                _FakeModelManager(),
        )

        output_path = tmp_path / "dubbed_audio.wav"

        pipeline.execute(
                VideoDubbingRequest(
                        translated_text_path=translation_path,
                        language="mr",
                        voice="ignored",
                        output_path=output_path,
                )
        )

        assert output_path.exists()
        assert len(tts_service.calls) >= 2
