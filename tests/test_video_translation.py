"""
===============================================================================
Bhasha Mitra - Video Translation Validation
-------------------------------------------------------------------------------
Flow

Video
   ↓
Extract Audio
   ↓
Faster Whisper
   ↓
English Transcript
   ↓
Sentence Chunking
   ↓
NLLB Translation
   ↓
Marathi Transcript

Purpose
-------
End-to-end validation of the complete offline translation pipeline.

Author
------
Bhasha Mitra AI Team
===============================================================================
"""

from pathlib import Path

import json
import re
import subprocess
import tempfile
import traceback
import sys

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def banner(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


# -----------------------------------------------------------------------------
# Sentence Chunker
# -----------------------------------------------------------------------------

MAX_WORDS_PER_CHUNK = 220


def chunk_sentences(
    text: str,
) -> list[str]:
    """
    Split transcript into sentence-aware chunks.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    chunks = []

    current_chunk = []

    current_words = 0

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        sentence_words = len(
            sentence.split()
        )

        if (
            current_chunk
            and current_words + sentence_words
            > MAX_WORDS_PER_CHUNK
        ):

            chunks.append(
                " ".join(current_chunk)
            )

            current_chunk = []

            current_words = 0

        current_chunk.append(sentence)

        current_words += sentence_words

    if current_chunk:

        chunks.append(
            " ".join(current_chunk)
        )

    return chunks


try:

    banner(
        "BHASHA MITRA - VIDEO TRANSLATION TEST"
    )

    # ------------------------------------------------------------------
    # Import Framework
    # ------------------------------------------------------------------

    print("\n[1/7] Importing ModelManager...")

    from ai.model_manager.manager import (
        ModelManager,
    )

    print("PASS")

    # ------------------------------------------------------------------
    # Load Manifest
    # ------------------------------------------------------------------

    print("\n[2/7] Loading Manifest...")

    manifest_file = (
        PROJECT_ROOT
        / "config"
        / "manifest.json"
    )

    with open(
        manifest_file,
        "r",
        encoding="utf-8",
    ) as f:

        manifest = json.load(f)

    ffmpeg_path = Path(
        manifest["ffmpeg"]["path"]
    )

    if not ffmpeg_path.is_absolute():

        ffmpeg_path = (
            manifest_file.parent
            / ffmpeg_path
        ).resolve()

    ffmpeg = (
        ffmpeg_path
        / "ffmpeg.exe"
    )

    if not ffmpeg.exists():

        raise FileNotFoundError(
            f"FFmpeg not found:\n{ffmpeg}"
        )

    print("PASS")

    # ------------------------------------------------------------------
    # Initialize Framework
    # ------------------------------------------------------------------

    print("\n[3/7] Initializing Framework...")

    manager = ModelManager()

    manager.initialize()

    print("PASS")

    # ------------------------------------------------------------------
    # Load Models
    # ------------------------------------------------------------------

    print("\n[4/7] Loading Models...")

    whisper = manager.load_model(
        category="asr",
        model="medium",
    )

    translation = manager.load_model(
        category="translation",
        model="NLLB-600M",
    )

    model = translation["model"]

    tokenizer = translation["tokenizer"]

    print("PASS")

    # ------------------------------------------------------------------
    # Input Video
    # ------------------------------------------------------------------

    video = input(
        "\nEnter video path : "
    ).strip()

    video = Path(video)

    if not video.exists():

        raise FileNotFoundError(video)

    # ------------------------------------------------------------------
    # Extract Audio
    # ------------------------------------------------------------------

    print("\n[5/7] Extracting Audio...")

    audio = (
        Path(tempfile.gettempdir())
        / "bhasha_mitra.wav"
    )

    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print("PASS")

    # ------------------------------------------------------------------
    # Speech Recognition
    # ------------------------------------------------------------------

    print("\n[6/7] Speech Recognition...")

    segments, info = whisper.transcribe(
        str(audio)
    )

    english = ""

    for segment in segments:

        english += (
            segment.text.strip()
            + " "
        )

    english = english.strip()

    print("\nEnglish Transcript")
    print("-" * 80)
    print(english)

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    print("\n[7/7] Translating...")


        # ------------------------------------------------------------------
    # Configure NLLB
    # ------------------------------------------------------------------

    tokenizer.src_lang = "eng_Latn"

    # ------------------------------------------------------------------
    # Sentence Chunking
    # ------------------------------------------------------------------

    chunks = chunk_sentences(
        english
    )

    print(
        f"\nTotal Chunks : {len(chunks)}"
    )

    translations = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        print(
            f"Translating Chunk "
            f"{index}/{len(chunks)}"
        )

        inputs = tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            max_length=1024,
        )

        with torch.inference_mode():

            generated = model.generate(
                **inputs,
                forced_bos_token_id=
                tokenizer.convert_tokens_to_ids(
                    "mar_Deva"
                ),
                num_beams=1,
                do_sample=False,
                max_new_tokens=256,
                repetition_penalty=1.10,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        translated = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
        )[0]

        translations.append(
            translated
        )

    marathi = "\n".join(
        translations
    )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    print(
        "\nTranslation Statistics"
    )

    print("-" * 80)

    print(
        f"English Words : "
        f"{len(english.split())}"
    )

    print(
        f"Chunks        : "
        f"{len(chunks)}"
    )

    print(
        f"Marathi Words : "
        f"{len(marathi.split())}"
    )

    # ------------------------------------------------------------------
    # Save Transcripts
    # ------------------------------------------------------------------

    english_file = (
        PROJECT_ROOT
        / "english_transcript.txt"
    )

    marathi_file = (
        PROJECT_ROOT
        / "marathi_transcript.txt"
    )

    english_file.write_text(
        english,
        encoding="utf-8",
    )

    marathi_file.write_text(
        marathi,
        encoding="utf-8",
    )

        # ------------------------------------------------------------------
    # Marathi Transcript
    # ------------------------------------------------------------------

    print("\nMarathi Transcript")
    print("-" * 80)
    print(marathi)

    # ------------------------------------------------------------------
    # Output Files
    # ------------------------------------------------------------------

    print("\nSaved Files")
    print("-" * 80)

    print(f"English Transcript : {english_file}")
    print(f"Marathi Transcript : {marathi_file}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    if audio.exists():
        audio.unlink()

    # ------------------------------------------------------------------
    # Completed
    # ------------------------------------------------------------------

    banner(
        "VIDEO TRANSLATION TEST PASSED"
    )

except Exception as exc:

    banner(
        "VIDEO TRANSLATION TEST FAILED"
    )

    print(type(exc).__name__)
    print(exc)
    print()

    traceback.print_exc()

    try:

        if (
            "audio" in locals()
            and audio.exists()
        ):
            audio.unlink()

    except Exception:
        pass