import json
from pathlib import Path

from ai.voice_cloning.service import VoiceDubbingService


def test_merge_transcript_and_translation_segments(tmp_path):
    transcript_path = tmp_path / "transcript.json"
    translation_path = tmp_path / "translation.json"

    transcript_path.write_text(
        json.dumps(
            {
                "segments": [
                    {"id": 1, "start": 0.0, "end": 2.0, "text": "hello world"}
                ]
            }
        ),
        encoding="utf-8",
    )

    translation_path.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 2.0,
                        "translated_text": "hola mundo",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    merged = VoiceDubbingService._merge_segments(
        transcript_path=transcript_path,
        translation_path=translation_path,
    )

    assert len(merged) == 1
    assert merged[0]["source_text"] == "hello world"
    assert merged[0]["translated_text"] == "hola mundo"
    assert merged[0]["start"] == 0.0
    assert merged[0]["end"] == 2.0


def test_merge_translation_without_source_text_keeps_transcript_text(tmp_path):
    transcript_path = tmp_path / "transcript.json"
    translation_path = tmp_path / "translation.json"

    transcript_path.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 5.0,
                        "text": "Namaskar mitranno",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    translation_path.write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 5.0,
                        "translated_text": "नमस्कार मित्रांनो",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    merged = VoiceDubbingService._merge_segments(
        transcript_path=transcript_path,
        translation_path=translation_path,
    )

    assert merged[0]["source_text"] == "Namaskar mitranno"
