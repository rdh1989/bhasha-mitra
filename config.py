"""Central configuration: paths, language table, runtime knobs."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
CACHE_DIR = BASE_DIR / ".cache"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

for _d in (UPLOADS_DIR, OUTPUTS_DIR, CACHE_DIR, LOGS_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"

LOG_FILE = LOGS_DIR / "app.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

_CPU_COUNT = os.cpu_count() or 4
# How many translation jobs may run at the same time.
MAX_CONCURRENT_JOBS = max(1, int(os.environ.get("MAX_CONCURRENT_JOBS", "5")))

ASR_MODEL_SIZE = os.environ.get("ASR_MODEL_SIZE", "small")  # tiny|small|medium
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

TRANSLATION_MODEL_DIR = MODELS_DIR / "translation" / "indictrans2-en-indic-dist-200M"

TTS_MODEL_DIR = MODELS_DIR / "tts" / "indic-parler-tts"
# The TTS model's "description" (style prompt) tower reuses the flan-t5-large
# tokenizer. It is not bundled with the model, so it is fetched once from the
# Hugging Face Hub (tokenizer files only, a few MB) and cached here for
# fully-offline reuse afterwards.
TTS_DESCRIPTION_TOKENIZER_ID = "google/flan-t5-large"
TTS_DESCRIPTION_TOKENIZER_CACHE = MODELS_DIR / "tts" / "_description_tokenizer_cache"

APP_USERNAME = os.environ.get("APP_USERNAME", "admin")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin")
# Seed values for the one-time default admin user created in the SQLite DB.
DEFAULT_ADMIN_USERNAME = APP_USERNAME
DEFAULT_ADMIN_PASSWORD = APP_PASSWORD


def _load_or_create_session_secret() -> str:
    """Persist a random session secret across restarts so logins survive a
    server restart, unless one is explicitly provided via SESSION_SECRET."""
    env_secret = os.environ.get("SESSION_SECRET")
    if env_secret:
        return env_secret
    secret_file = DATA_DIR / "session_secret.key"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    secret = os.urandom(32).hex()
    secret_file.write_text(secret, encoding="utf-8")
    return secret


SESSION_SECRET = _load_or_create_session_secret()

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))  # 2 GiB
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

# Languages faster-whisper (OpenAI Whisper) can reliably transcribe. Several
# very low-resource Indic languages above (Bodo, Dogri, Konkani, Maithili,
# Manipuri, Santali, Odia) are NOT in Whisper's training set, so they cannot
# be used as *source* audio language, only as *target* dub languages.
WHISPER_SUPPORTED_SOURCE_CODES = {
    "en", "hi", "mr", "bn", "gu", "kn", "ml", "ta", "te", "ur", "pa", "sa", "sd", "ne", "as",
}
