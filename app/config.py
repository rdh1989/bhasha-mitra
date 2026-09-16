"""Central configuration: paths, language table, runtime knobs."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running as a PyInstaller-built exe (see build.py): large local assets
    # (models/data/outputs/logs/uploads) are never bundled into the exe, so
    # look for them next to the actual .exe file instead of inside the
    # (extracted, code-only) bundle.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
OUTPUTS_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / ".cache"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

for _d in (OUTPUTS_DIR, CACHE_DIR, LOGS_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"

LOG_FILE = LOGS_DIR / "app.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Prefer the full ffmpeg/ffprobe build under models/third_party/ffmpeg over
# imageio-ffmpeg's older bundled binary (see app/media.py) - falls back to
# imageio-ffmpeg automatically if this folder isn't present.
_THIRD_PARTY_FFMPEG_DIR = MODELS_DIR / "third_party" / "ffmpeg"
_THIRD_PARTY_FFMPEG_BIN_DIRS = sorted(_THIRD_PARTY_FFMPEG_DIR.glob("*/bin")) if _THIRD_PARTY_FFMPEG_DIR.is_dir() else []
FFMPEG_EXE = str(_THIRD_PARTY_FFMPEG_BIN_DIRS[-1] / "ffmpeg.exe") if _THIRD_PARTY_FFMPEG_BIN_DIRS else None
FFPROBE_EXE = str(_THIRD_PARTY_FFMPEG_BIN_DIRS[-1] / "ffprobe.exe") if _THIRD_PARTY_FFMPEG_BIN_DIRS else None

_CPU_COUNT = os.cpu_count() or 4
# How many translation jobs may run at the same time.
MAX_CONCURRENT_JOBS = max(1, int(os.environ.get("MAX_CONCURRENT_JOBS", "5")))
MAX_PARALLEL_TRANSLATION_JOBS = max(1, int(os.environ.get("MAX_PARALLEL_TRANSLATION_JOBS", "3")))

# Medium Whisper substantially improves difficult Indic narration over the
# small checkpoint. Set ASR_MODEL_SIZE=small only when throughput matters more
# than transcript accuracy.
ASR_MODEL_SIZE = os.environ.get("ASR_MODEL_SIZE", "medium")  # tiny|small|medium
ASR_MODEL_DIR = MODELS_DIR / "asr" / "faster_whisper" / ASR_MODEL_SIZE
ASR_COMPUTE_TYPE = os.environ.get("ASR_COMPUTE_TYPE", "int8")
# CPU threads used for each transcription. Defaults to all cores, since most
# of the time only one or two jobs are actually running at once and a single
# job's ASR/TTS pass should not be artificially slowed down. If you routinely
# run many (e.g. 5) jobs at the exact same time on a low-core machine, lower
# this explicitly to avoid oversubscription.
ASR_CPU_THREADS = int(os.environ.get("ASR_CPU_THREADS", str(_CPU_COUNT)))
# faster-whisper/CTranslate2 can safely serve several concurrent transcribe()
# calls on the same loaded model when given more than one internal worker.
ASR_NUM_WORKERS = max(1, int(os.environ.get("ASR_NUM_WORKERS", str(MAX_CONCURRENT_JOBS))))
# Global PyTorch intra-op thread cap (translation + TTS models). Defaults to
# all cores for the same reason as ASR_CPU_THREADS above - lower explicitly
# if you need to dedicate headroom for several simultaneous heavy jobs.
TORCH_NUM_THREADS = max(1, int(os.environ.get("TORCH_NUM_THREADS", str(_CPU_COUNT))))

# AI4Bharat IndicConformer: a specialized 22-language Indic ASR model (ONNX
# Memory policy: protect against OOM during model loading and translation jobs.
# These settings apply to the entire application process memory footprint,
# not just individual models.
# 
# MEMORY_USAGE_LIMIT_PERCENT: Maximum process memory as % of physical RAM (10-90, default 70).
#   On a 24 GB machine, 70% = ~16.8 GB available for models, runtime temp memory, etc.
# 
# MEMORY_SAFETY_MARGIN_GB: Reserve to keep free for system operations (default 0.5).
#   Hard limit = (physical_memory * percent) - safety_margin
# 
# MEMORY_WARNING_THRESHOLD_PERCENT: Warn when approaching hard limit (default 60 of limit %).
#   Warnings trigger when process memory exceeds this threshold but are not blocking.
# 
# MEMORY_POLICY_ENABLED: Enable/disable admission control (default true).
#   When enabled, model loading is rejected if it would exceed the memory policy.
#   When disabled, models load without memory checks (not recommended).
MEMORY_USAGE_LIMIT_PERCENT = int(os.environ.get("MEMORY_USAGE_LIMIT_PERCENT", "70"))
MEMORY_SAFETY_MARGIN_GB = float(os.environ.get("MEMORY_SAFETY_MARGIN_GB", "0.5"))
MEMORY_POLICY_ENABLED = os.environ.get("MEMORY_POLICY_ENABLED", "true").strip().lower() in ("1", "true", "yes")
MEMORY_WARNING_THRESHOLD_PERCENT = int(os.environ.get("MEMORY_WARNING_THRESHOLD_PERCENT", "60"))

# AI4Bharat IndicConformer: a specialized 22-language Indic ASR model (ONNX
# CTC/RNNT) used to re-transcribe each Whisper-segmented clip for
# higher-quality, native-script text than Whisper's general-purpose decoder,
# without slowing down language detection/segmentation (still handled by the
# lighter Whisper pass). See app/models/indic_asr.py.
INDIC_ASR_MODEL_DIR = MODELS_DIR / "asr" / "indic-conformer-600m-multilingual"
# Whisper remains the transcript authority. Per-segment IndicConformer output
# can truncate words at segment edges and should be enabled only for a source
# language where it has been evaluated against the actual media.
INDIC_ASR_ENABLED = os.environ.get("INDIC_ASR_ENABLED", "false").strip().lower() in ("1", "true", "yes")
# "ctc" (fast, default) or "rnnt" (also fast on CPU via ONNX, occasionally
# more accurate on tricky audio).
INDIC_ASR_DECODING = os.environ.get("INDIC_ASR_DECODING", "ctc").strip().lower()
ASR_VAD_THRESHOLD = float(os.environ.get("ASR_VAD_THRESHOLD", os.environ.get("INDIC_ASR_VAD_THRESHOLD", "0.5")))
ASR_VAD_MIN_SILENCE_MS = max(0, int(os.environ.get("ASR_VAD_MIN_SILENCE_MS", os.environ.get("INDIC_ASR_VAD_MIN_SILENCE_MS", "600"))))
ASR_VAD_SPEECH_PADDING_MS = max(0, int(os.environ.get("ASR_VAD_SPEECH_PADDING_MS", os.environ.get("INDIC_ASR_VAD_SPEECH_PADDING_MS", "0"))))
ASR_REFINE_ENABLED = os.environ.get("ASR_REFINE_ENABLED", "true").strip().lower() in ("1", "true", "yes")
ASR_REFINE_MIN_PAUSE_SECONDS = max(0.2, float(os.environ.get("ASR_REFINE_MIN_PAUSE_SECONDS", "0.5")))
ASR_REFINE_MAX_INSIGNIFICANT_SILENCE_SECONDS = max(
    0.0, float(os.environ.get("ASR_REFINE_MAX_INSIGNIFICANT_SILENCE_SECONDS", "0.25"))
)
ASR_REFINE_MIN_EVENT_DURATION_SECONDS = max(
    0.2, float(os.environ.get("ASR_REFINE_MIN_EVENT_DURATION_SECONDS", "0.8"))
)
ASR_REFINE_MIN_FRAGMENT_WORDS = max(1, int(os.environ.get("ASR_REFINE_MIN_FRAGMENT_WORDS", "2")))
ASR_REFINE_SAFE_BOUNDARY_WINDOW_SECONDS = max(
    0.05, float(os.environ.get("ASR_REFINE_SAFE_BOUNDARY_WINDOW_SECONDS", "0.8"))
)
ASR_REFINE_SILENCE_THRESHOLD = max(
    0.0001, float(os.environ.get("ASR_REFINE_SILENCE_THRESHOLD", "0.01"))
)
TRANSLATION_CONTEXT_MAX_EVENTS = max(1, int(os.environ.get("TRANSLATION_CONTEXT_MAX_EVENTS", "3")))
TRANSLATION_CONTEXT_MAX_CHARACTERS = max(
    100, int(os.environ.get("TRANSLATION_CONTEXT_MAX_CHARACTERS", "1200"))
)
TRANSLATION_CONTEXT_MIN_FRAGMENT_WORDS = max(
    1, int(os.environ.get("TRANSLATION_CONTEXT_MIN_FRAGMENT_WORDS", "2"))
)
INDIC_ASR_MAX_INFERENCE_DURATION_SECONDS = max(
    1.0, float(os.environ.get("INDIC_ASR_MAX_INFERENCE_DURATION_SECONDS", "15"))
)
INDIC_ASR_CHUNK_OVERLAP_SECONDS = min(
    max(0.0, float(os.environ.get("INDIC_ASR_CHUNK_OVERLAP_SECONDS", "1"))),
    INDIC_ASR_MAX_INFERENCE_DURATION_SECONDS - 0.01,
)

# "1B" (bigger, non-distilled) or "dist" (smaller distilled checkpoints).
# The 1B models are the default because they provide the best observed speed
# and translation quality in this deployment; use dist only when a smaller
# memory footprint is specifically required.
TRANSLATION_MODEL_SIZE = os.environ.get("TRANSLATION_MODEL_SIZE", "1B").strip()
TRANSLATION_CONTEXT_ENABLED = os.environ.get("TRANSLATION_CONTEXT_ENABLED", "true").strip().lower() in ("1", "true", "yes")
TRANSLATION_CONTEXT_MAX_EVENTS = max(1, int(os.environ.get("TRANSLATION_CONTEXT_MAX_EVENTS", "3")))
TRANSLATION_CONTEXT_MAX_CHARS = max(100, int(os.environ.get("TRANSLATION_CONTEXT_MAX_CHARS", "1200")))
TRANSLATION_CONTEXT_MAX_DURATION_SECONDS = max(1.0, float(os.environ.get("TRANSLATION_CONTEXT_MAX_DURATION_SECONDS", "30")))
TRANSLATION_CONTEXT_MAX_SOURCE_TOKENS = max(32, int(os.environ.get("TRANSLATION_CONTEXT_MAX_SOURCE_TOKENS", "192")))
DOMAIN_PACK_ENABLED = os.environ.get("DOMAIN_PACK_ENABLED", "true").strip().lower() in ("1", "true", "yes")
ACTIVE_DOMAIN_PACK_PATH = Path(os.environ.get("ACTIVE_DOMAIN_PACK_PATH", str(BASE_DIR / "domains" / "agriculture" / "knowledge.json")))

TRANSLATION_MODEL_DIR = MODELS_DIR / "translation" / (
    "indictrans2-en-indic-1B" if TRANSLATION_MODEL_SIZE == "1B" else "indictrans2-en-indic-dist-200M"
)
# Direct Indic -> Indic translation (e.g. Marathi -> Hindi) without pivoting
# through English, which used to lose quality via a double translation.
TRANSLATION_INDIC_INDIC_MODEL_DIR = MODELS_DIR / "translation" / (
    "indictrans2-indic-indic-1B" if TRANSLATION_MODEL_SIZE == "1B" else "indictrans2-indic-indic-dist-320M"
)
# Direct Indic -> English translation, so dubbing to English no longer needs
# Whisper's own (less reliable) speech-to-English "translate" task - the
# already-transcribed source segments are translated with this model instead.
TRANSLATION_INDIC_EN_MODEL_DIR = MODELS_DIR / "translation" / (
    "indictrans2-indic-en-1B" if TRANSLATION_MODEL_SIZE == "1B" else "indictrans2-indic-en-dist-200M"
)
# Direct IndicTrans2 is the intended one-pass route for Indic-to-Indic pairs.
# An English pivot adds a second generative step and should be used only after
# pair-specific evaluation demonstrates it is better.
INDIC_TO_INDIC_USE_ENGLISH_PIVOT = os.environ.get("INDIC_TO_INDIC_USE_ENGLISH_PIVOT", "false").strip().lower() in (
    "1", "true", "yes",
)

# "piper" (fast, ONNX, CPU-friendly) or "parler" (Indic Parler-TTS, slower but
# more expressive/style-controllable). Piper is the default since it runs
# roughly an order of magnitude faster than Indic Parler-TTS on CPU.
TTS_ENGINE = os.environ.get("TTS_ENGINE", "piper").strip().lower()

TTS_MODEL_DIR = MODELS_DIR / "tts" / "indic-parler-tts"
# The TTS model's "description" (style prompt) tower reuses the flan-t5-large
# tokenizer. It is not bundled with the model, so it is fetched once from the
# Hugging Face Hub (tokenizer files only, a few MB) and cached here for
# fully-offline reuse afterwards.
TTS_DESCRIPTION_TOKENIZER_ID = "google/flan-t5-large"
TTS_DESCRIPTION_TOKENIZER_CACHE = MODELS_DIR / "tts" / "_description_tokenizer_cache"

PIPER_VOICES_DIR = MODELS_DIR / "tts" / "piper-voices"
# Language used for Piper synthesis when the target language has no dedicated
# Piper voice available (see app/models/piper_tts.py's voice table).
PIPER_DEFAULT_VOICE_LANG = os.environ.get("PIPER_DEFAULT_VOICE_LANG", "mr")

# TTS prosody controls. These affect only subdivision, Piper rate selection,
# and conservative audio finishing; ASR and translation timestamps stay intact.
TTS_PROSODY_ENABLED = os.environ.get("TTS_PROSODY_ENABLED", "true").strip().lower() in ("1", "true", "yes")
TTS_MIN_PAUSE_SECONDS = max(0.2, float(os.environ.get("TTS_MIN_PAUSE_SECONDS", "0.35")))
TTS_MAX_PAUSE_SECONDS = max(TTS_MIN_PAUSE_SECONDS, float(os.environ.get("TTS_MAX_PAUSE_SECONDS", "1.5")))
TTS_SILENCE_THRESHOLD = max(0.0001, float(os.environ.get("TTS_SILENCE_THRESHOLD", "0.015")))
TTS_MAX_UNIT_CHARACTERS = max(60, int(os.environ.get("TTS_MAX_UNIT_CHARACTERS", "125")))
TTS_MIN_UNIT_SECONDS = max(0.5, float(os.environ.get("TTS_MIN_UNIT_SECONDS", "0.8")))
TTS_RATE_TOLERANCE = min(0.3, max(0.02, float(os.environ.get("TTS_RATE_TOLERANCE", "0.08"))))
TTS_PIPER_LENGTH_SCALE_MIN = min(1.0, max(0.5, float(os.environ.get("TTS_PIPER_LENGTH_SCALE_MIN", "0.9"))))
TTS_PIPER_LENGTH_SCALE_MAX = max(1.0, min(1.5, float(os.environ.get("TTS_PIPER_LENGTH_SCALE_MAX", "1.1"))))
# Speed multipliers used for the natural-rate retry and bounded post-TTS fit.
TTS_MIN_SPEED = min(1.0, max(0.5, float(os.environ.get("TTS_MIN_SPEED", "0.85"))))
TTS_MAX_SPEED = max(1.0, min(1.5, float(os.environ.get("TTS_MAX_SPEED", "1.15"))))
TTS_MAX_POST_STRETCH = TTS_MAX_SPEED
TTS_MAX_ALLOWED_COMPRESSION = max(
    TTS_MAX_SPEED, min(2.0, float(os.environ.get("TTS_MAX_ALLOWED_COMPRESSION", "1.5")))
)
TTS_MAX_ALLOWED_EXPANSION = min(
    1.0, max(0.5, float(os.environ.get("TTS_MAX_ALLOWED_EXPANSION", "0.85")))
)
TTS_SHORT_SEGMENT_SECONDS = max(0.1, float(os.environ.get("TTS_SHORT_SEGMENT_SECONDS", "1.0")))
TTS_NATURAL_FIT_THRESHOLD = max(1.0, float(os.environ.get("TTS_NATURAL_FIT_THRESHOLD", "1.05")))
TTS_MILD_ADJUSTMENT_THRESHOLD = max(
    TTS_NATURAL_FIT_THRESHOLD, float(os.environ.get("TTS_MILD_ADJUSTMENT_THRESHOLD", "1.15"))
)
TTS_REPLAN_THRESHOLD = max(
    TTS_MILD_ADJUSTMENT_THRESHOLD, float(os.environ.get("TTS_REPLAN_THRESHOLD", "1.25"))
)
TTS_PRESERVE_INTENSITY = os.environ.get("TTS_PRESERVE_INTENSITY", "true").strip().lower() in ("1", "true", "yes")
TTS_INTENSITY_GAIN_MIN = min(1.0, max(0.5, float(os.environ.get("TTS_INTENSITY_GAIN_MIN", "0.85"))))
TTS_INTENSITY_GAIN_MAX = max(1.0, min(1.5, float(os.environ.get("TTS_INTENSITY_GAIN_MAX", "1.15"))))

APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
# Seed values for the one-time default admin user created in the SQLite DB.
DEFAULT_ADMIN_USERNAME = APP_USERNAME
DEFAULT_ADMIN_PASSWORD = APP_PASSWORD


def _load_or_create_session_secret() -> str:
    """A fresh random secret every process start invalidates any previously
    issued session cookies, so every app launch requires logging in again -
    unless one is explicitly pinned via SESSION_SECRET (e.g. so a supervisor
    that restarts the process on crash doesn't log everyone out)."""
    env_secret = os.environ.get("SESSION_SECRET")
    if env_secret:
        return env_secret
    return os.urandom(32).hex()


SESSION_SECRET = _load_or_create_session_secret()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}


@dataclass(frozen=True)
class Language:
    code: str  # short id used in UI + matched against whisper's detected language
    label: str
    flores_code: str  # IndicTrans2 / FLORES-200 tag
    tts_speakers: tuple[str, ...] | None = None


# Target languages: intersection of what IndicTrans2 (en->indic) and
# Indic Parler-TTS both support, plus English itself.
LANGUAGES: list[Language] = [
    Language("en", "English", "eng_Latn", ("Thoma", "Mary")),
    Language("hi", "Hindi", "hin_Deva", ("Rohit", "Divya")),
    Language("mr", "Marathi", "mar_Deva", ("Sanjay", "Sunita")),
    Language("bn", "Bengali", "ben_Beng", ("Arjun", "Aditi")),
    Language("gu", "Gujarati", "guj_Gujr", ("Yash", "Neha")),
    Language("kn", "Kannada", "kan_Knda", ("Suresh", "Anu")),
    Language("ml", "Malayalam", "mal_Mlym", ("Anjali", "Harish")),
    Language("or", "Odia", "ory_Orya", ("Manas", "Debjani")),
    Language("pa", "Punjabi", "pan_Guru", ("Divjot", "Gurpreet")),
    Language("ta", "Tamil", "tam_Taml", ("Jaya",)),
    Language("te", "Telugu", "tel_Telu", ("Prakash", "Lalitha")),
    Language("ur", "Urdu", "urd_Arab", None),
    Language("as", "Assamese", "asm_Beng", ("Amit", "Sita")),
    Language("ne", "Nepali", "npi_Deva", ("Amrita",)),
    Language("sa", "Sanskrit", "san_Deva", ("Aryan",)),
    Language("brx", "Bodo", "brx_Deva", ("Bikram", "Maya")),
    Language("doi", "Dogri", "doi_Deva", ("Karan",)),
    Language("mni", "Manipuri", "mni_Mtei", ("Laishram", "Ranjit")),
    Language("gom", "Konkani", "gom_Deva", None),
    Language("mai", "Maithili", "mai_Deva", None),
    Language("sd", "Sindhi", "snd_Deva", None),
    Language("sat", "Santali", "sat_Olck", None),
    Language("ks", "Kashmiri", "kas_Arab", None),
]

LANGUAGES_BY_CODE = {lang.code: lang for lang in LANGUAGES}

INDIC_ASR_SUPPORTED_SOURCE_CODES = {
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "gom", "ks", "mai",
    "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd", "ta",
    "te", "ur",
}
ASR_PROVIDER_BY_LANGUAGE = {
    "en": "faster_whisper",
    **{code: "indicconformer" for code in INDIC_ASR_SUPPORTED_SOURCE_CODES},
}

# Languages faster-whisper (OpenAI Whisper) can reliably transcribe. Several
# very low-resource Indic languages above (Bodo, Dogri, Konkani, Maithili,
# Manipuri, Santali, Odia) are NOT in Whisper's training set, so they cannot
# be used as *source* audio language, only as *target* dub languages.
WHISPER_SUPPORTED_SOURCE_CODES = {
    "en", "hi", "mr", "bn", "gu", "kn", "ml", "ta", "te", "ur", "pa", "sa", "sd", "ne", "as",
}
