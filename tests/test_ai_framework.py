"""
===============================================================================
Bhasha Mitra
AI Framework Smoke Test
===============================================================================
"""

from pathlib import Path
import sys
import traceback

# ---------------------------------------------------------------------
# Project Root
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("BHASHA MITRA AI FRAMEWORK VALIDATION")
print("=" * 80)

try:

    # -----------------------------------------------------------------
    # Step 1
    # -----------------------------------------------------------------

    print("\n[1/8] Importing ModelManager...")

    from ai.model_manager.manager import ModelManager

    print("PASS")

    # -----------------------------------------------------------------
    # Step 2
    # -----------------------------------------------------------------

    print("\n[2/8] Creating ModelManager...")

    manager = ModelManager()

    print("PASS")

    # -----------------------------------------------------------------
    # Step 3
    # -----------------------------------------------------------------

    print("\n[3/8] Initializing Model Manager...")

    manager.initialize()

    print("PASS")

    # -----------------------------------------------------------------
    # Step 4
    # -----------------------------------------------------------------

    print("\n[4/8] Registered Assets")

    for item in manager._registry.list():
        print(f"   ✓ {item}")

    # -----------------------------------------------------------------
    # Step 5
    # -----------------------------------------------------------------

    print("\n[5/8] Loading ASR Model...")

    whisper = manager.load_model(
        category="asr",
        model="tiny",
    )

    print("PASS")
    print(type(whisper).__name__)

    # -----------------------------------------------------------------
    # Step 6
    # -----------------------------------------------------------------

    print("\n[6/8] Cache Validation...")

    whisper2 = manager.load_model(
        category="asr",
        model="tiny",
    )

    if whisper is whisper2:
        print("PASS")
        print("Cache Working")
    else:
        print("FAILED")
        print("Cache NOT Working")

    # -----------------------------------------------------------------
    # Step 7
    # -----------------------------------------------------------------

    audio = input("\nAudio File : ").strip()

    audio = Path(audio)

    if not audio.exists():
        raise FileNotFoundError(audio)

    # -----------------------------------------------------------------
    # Step 8
    # -----------------------------------------------------------------

    print("\n[7/8] Running Transcription...\n")

    segments, info = whisper.transcribe(
        str(audio),
        beam_size=5,
    )

    print("=" * 80)

    print("Detected Language :", info.language)
    print("Probability       :", info.language_probability)

    print("\nTranscript\n")

    transcript = []

    for segment in segments:

        transcript.append(segment.text)

        print(
            f"[{segment.start:>6.2f} - "
            f"{segment.end:>6.2f}] "
            f"{segment.text}"
        )

    print("=" * 80)

    print("\nFull Transcript\n")

    print("".join(transcript))

    print("=" * 80)

    manager.shutdown()

    print("\nFRAMEWORK VALIDATION PASSED")

except Exception as exc:

    print("\n")
    print("=" * 80)
    print("FRAMEWORK VALIDATION FAILED")
    print("=" * 80)

    print(type(exc).__name__)
    print(exc)

    print("\n")

    traceback.print_exc()