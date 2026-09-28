"""Central configuration: paths, language table, runtime knobs."""
from __future__ import annotations

import os
import json
import copy
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "Bhasha Mitra"
APP_VERSION = "1.1.0"
APP_BUILD = os.environ.get("BHASHAMITRA_APP_BUILD", "DEV")

def _resolve_runtime_root(*, frozen: bool | None = None, executable: str | None = None) -> Path:
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if is_frozen:
        return Path(executable or sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RUNTIME_ROOT = _resolve_runtime_root()
# Compatibility aliases retained for existing consumers; runtime paths must use RUNTIME_ROOT.
APPLICATION_DIR = RUNTIME_ROOT
APPLICATION_PARENT = RUNTIME_ROOT
BASE_DIR = RUNTIME_ROOT

CONFIG_DEFAULTS_DIR = Path(__file__).resolve().parent.parent / "config_defaults"

_RUNTIME_DIRECTORIES = {
    "config": "config",
    "models": "models",
    "data": "data",
    "logs": "logs",
    "output": "output",
    "cache": "cache",
}
_LEGACY_RUNTIME_DIRECTORIES = {
    "config": ("Config", "BhashaMitra-Config"),
    "models": ("Models", "BhashaMitra-Models"),
    "data": ("Data", "BhashaMitra-Data"),
    "logs": ("Logs", "BhashaMitra-Logs"),
    "output": ("Outputs", "BhashaMitra-Outputs"),
    "cache": ("Cache", "BhashaMitra-Cache"),
}


def _resolve_runtime_directories(runtime_root: Path) -> dict[str, Path]:
    return {key: runtime_root / name for key, name in _RUNTIME_DIRECTORIES.items()}


def _ensure_runtime_directories(runtime_root: Path) -> dict[str, Path]:
    paths = _resolve_runtime_directories(runtime_root)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _copy_legacy_contents(source: Path, destination: Path) -> None:
    """Copy legacy runtime state without deleting or overwriting either tree."""
    if not source.is_dir() or destination.exists():
        return
    logger_message = f"Legacy runtime directory found at {source}; copying contents to {destination}."
    print(logger_message)
    shutil.copytree(source, destination)


for _runtime_key, _runtime_name in _RUNTIME_DIRECTORIES.items():
    if not (RUNTIME_ROOT / _runtime_name).exists():
        for _legacy_name in _LEGACY_RUNTIME_DIRECTORIES[_runtime_key]:
            if (RUNTIME_ROOT / _legacy_name).is_dir():
                _copy_legacy_contents(
                    RUNTIME_ROOT / _legacy_name,
                    RUNTIME_ROOT / _runtime_name,
                )
                break

_RUNTIME_PATHS = _ensure_runtime_directories(RUNTIME_ROOT)
CONFIG_DIR = _RUNTIME_PATHS["config"]


def _load_json_config(filename: str) -> dict:
    defaults_path = CONFIG_DEFAULTS_DIR / filename
    external_path = CONFIG_DIR / filename
    if not external_path.exists():
        if not defaults_path.is_file():
            raise FileNotFoundError(f"Missing external configuration and default: {external_path}")
        shutil.copy2(defaults_path, external_path)
    try:
        payload = json.loads(external_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid configuration file: {external_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Configuration file must contain a JSON object: {external_path}")
    if not defaults_path.is_file():
        return payload
    try:
        defaults = json.loads(defaults_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid default configuration file: {defaults_path}: {exc}") from exc

    def merge(default_value, configured_value):
        if isinstance(default_value, dict) and isinstance(configured_value, dict):
            merged = {key: merge(value, configured_value[key]) if key in configured_value else value
                      for key, value in default_value.items()}
            merged.update({key: value for key, value in configured_value.items() if key not in default_value})
            return merged
        return configured_value

    return merge(defaults, payload)


APP_CONFIG = _load_json_config("app.json")
MODELS_CONFIG = _load_json_config("models.json")


def _normalize_model_paths(config: dict) -> dict:
    """Accept old catalog prefixes while keeping paths relative to MODELS_DIR."""
    normalized = copy.deepcopy(config)
    for section in normalized.get("asr", {}).values():
        for model in section.get("models", {}).values() if isinstance(section, dict) else ():
            if isinstance(model.get("path"), str) and model["path"].startswith("models/"):
                model["path"] = model["path"][len("models/"):]
    for route in normalized.get("translation", {}).values():
        for model in route.get("models", {}).values() if isinstance(route, dict) else ():
            if isinstance(model.get("path"), str) and model["path"].startswith("models/"):
                model["path"] = model["path"][len("models/"):]
    for model in normalized.get("tts", {}).get("models", {}).values():
        if isinstance(model.get("path"), str) and model["path"].startswith("models/"):
            model["path"] = model["path"][len("models/"):]
    cache_path = normalized.get("tts", {}).get("description_tokenizer_cache_directory")
    if isinstance(cache_path, str) and cache_path.startswith("models/"):
        normalized["tts"]["description_tokenizer_cache_directory"] = cache_path[len("models/"):]
    return normalized


MODELS_CONFIG = _normalize_model_paths(MODELS_CONFIG)
LANGUAGES_CONFIG = _load_json_config("languages.json")


def _normalize_legacy_models_config(config: dict) -> dict:
    """Map the pre-catalog external file into the current catalog in memory."""
    normalized = copy.deepcopy(config)
    asr = normalized.get("asr", {})
    english = asr.get("english", {})
    if asr.get("model_size"):
        model_key = f"whisper_{asr['model_size']}"
        if model_key in english.get("models", {}):
            english["active_model"] = model_key
        legacy_path = asr.get("model_directory")
        if legacy_path and model_key in english.get("models", {}):
            english["models"][model_key]["path"] = legacy_path.format(size=asr["model_size"])
        if asr.get("compute_type") and model_key in english.get("models", {}):
            english["models"][model_key]["compute_type"] = asr["compute_type"]

    indic = asr.get("indic", {})
    legacy_indic = normalized.get("indic_asr", {})
    if legacy_indic:
        indic["enabled"] = legacy_indic.get("enabled", indic.get("enabled", False))
        model = indic.get("models", {}).get(indic.get("active_model"))
        if model is not None:
            model["path"] = legacy_indic.get("model_directory", model["path"])
            model["decoding"] = legacy_indic.get("decoding", model.get("decoding", "ctc"))

    translation = normalized.get("translation", {})
    legacy_translation = translation.get("model_size")
    if legacy_translation:
        size_key = "1B" if legacy_translation == "1B" else "dist"
        route_names = ("en_to_indic", "indic_to_indic", "indic_to_en")
        legacy_names = ("en_indic", "indic_indic", "indic_en")
        legacy_directories = translation.get("model_directories", {})
        for route_name, legacy_name in zip(route_names, legacy_names):
            route = translation.get(route_name, {})
            model_key = "indictrans2_1b" if size_key == "1B" else (
                "indictrans2_320m" if route_name == "indic_to_indic" else "indictrans2_200m"
            )
            if model_key in route.get("models", {}):
                route["active_model"] = model_key
                legacy_path = legacy_directories.get(legacy_name, {}).get(size_key)
                if legacy_path:
                    route["models"][model_key]["path"] = legacy_path

    tts = normalized.get("tts", {})
    if tts.get("engine") in tts.get("models", {}):
        tts["active_model"] = tts["engine"]
    for model_key, legacy_key in (("piper", "piper_voices_directory"), ("parler", "parler_model_directory")):
        if legacy_key in tts and model_key in tts.get("models", {}):
            tts["models"][model_key]["path"] = tts[legacy_key]
    asr.pop("model_size", None)
    asr.pop("model_directory", None)
    asr.pop("compute_type", None)
    normalized.pop("indic_asr", None)
    translation.pop("model_size", None)
    translation.pop("model_directories", None)
    translation.pop("memory", None)
    for key in ("engine", "piper_engine", "providers", "parler_model_directory", "piper_voices_directory"):
        tts.pop(key, None)
    return normalized


_external_models_payload = json.loads(
    (CONFIG_DIR / "models.json").read_text(encoding="utf-8")
)
if "english" not in _external_models_payload.get("asr", {}):
    MODELS_CONFIG = _normalize_legacy_models_config(MODELS_CONFIG)


def _validate_model_catalog(name: str, section: dict, supported_engines: set[str]) -> dict:
    if not isinstance(section, dict) or not isinstance(section.get("models"), dict):
        raise RuntimeError(f"models.json {name} catalog must contain a models object")
    active_model = section.get("active_model")
    models = section["models"]
    if active_model not in models:
        raise RuntimeError(f"models.json {name} active_model '{active_model}' is not defined")
    for model_key, model in models.items():
        required = {"enabled", "model_id", "path", "estimated_size_gb"}
        if not isinstance(model, dict) or not required.issubset(model):
            raise RuntimeError(f"models.json {name} model '{model_key}' is incomplete")
        if not isinstance(model["enabled"], bool) or not model["enabled"] and model_key == active_model:
            raise RuntimeError(f"models.json {name} active model '{active_model}' must be enabled")
        if not isinstance(model["path"], str) or not model["path"] or Path(model["path"]).is_absolute():
            raise RuntimeError(f"models.json {name} model '{model_key}' has an invalid path")
        if float(model["estimated_size_gb"]) < 0:
            raise RuntimeError(f"models.json {name} model '{model_key}' has invalid memory metadata")
        engine = model.get("engine")
        if supported_engines and engine not in supported_engines:
            raise RuntimeError(f"models.json {name} model '{model_key}' uses unsupported engine '{engine}'")
    return models[active_model]


def _validate_configuration() -> None:
    required_app_keys = {"log_level", "max_concurrent_jobs", "max_parallel_translation_jobs"}
    if not required_app_keys.issubset(APP_CONFIG):
        raise RuntimeError("app.json is missing required application settings")

    asr = MODELS_CONFIG.get("asr", {})
    translation = MODELS_CONFIG.get("translation", {})
    tts = MODELS_CONFIG.get("tts", {})
    if not {"english", "indic"}.issubset(asr):
        raise RuntimeError("models.json is missing ASR catalogs")
    if not {"en_to_indic", "indic_to_indic", "indic_to_en"}.issubset(translation):
        raise RuntimeError("models.json is missing translation route catalogs")
    if not isinstance(tts.get("active_model"), str):
        raise RuntimeError("models.json is missing the active TTS model")
    asr_english = _validate_model_catalog("asr.english", asr["english"], {"faster_whisper"})
    asr_indic = _validate_model_catalog("asr.indic", asr["indic"], {"indicconformer"})
    translation_models = {
        route: _validate_model_catalog(f"translation.{route}", translation[route], set())
        for route in ("en_to_indic", "indic_to_indic", "indic_to_en")
    }
    tts_model = _validate_model_catalog("tts", tts, {"piper", "parler"})
    if not isinstance(asr["indic"].get("enabled", True), bool):
        raise RuntimeError("models.json asr.indic enabled must be boolean")

    languages = LANGUAGES_CONFIG.get("languages")
    if not isinstance(languages, list) or not languages:
        raise RuntimeError("languages.json must contain a non-empty languages list")
    language_codes = set()
    valid_providers = {
        asr["english"]["models"][asr["english"]["active_model"]]["engine"],
        asr["indic"]["models"][asr["indic"]["active_model"]]["engine"],
    }
    required_language_keys = {"code", "label", "flores_code", "asr_provider", "whisper_supported"}
    for language in languages:
        if not isinstance(language, dict) or not required_language_keys.issubset(language):
            raise RuntimeError("languages.json contains an incomplete language mapping")
        if language["code"] in language_codes or language["asr_provider"] not in valid_providers:
            raise RuntimeError("languages.json contains an invalid language/provider mapping")
        language_codes.add(language["code"])
    overrides = LANGUAGES_CONFIG.get("asr_model_code_overrides", {})
    if not isinstance(overrides, dict) or not set(overrides).issubset(language_codes):
        raise RuntimeError("languages.json contains an invalid ASR language-code mapping")


EXTERNAL_MODELS_DIR = RUNTIME_ROOT / _RUNTIME_DIRECTORIES["models"]
MODELS_DIR = EXTERNAL_MODELS_DIR
OUTPUTS_DIR = RUNTIME_ROOT / _RUNTIME_DIRECTORIES["output"]
CACHE_DIR = RUNTIME_ROOT / _RUNTIME_DIRECTORIES["cache"]
LOGS_DIR = RUNTIME_ROOT / _RUNTIME_DIRECTORIES["logs"]
DATA_DIR = RUNTIME_ROOT / _RUNTIME_DIRECTORIES["data"]

_validate_configuration()


def _active_model(section_name: str, model_key: str | None = None) -> dict:
    section = MODELS_CONFIG[section_name] if model_key is None else MODELS_CONFIG[section_name][model_key]
    selected = section["models"][section["active_model"]]
    return {**selected, "path": MODELS_DIR / selected["path"]}


def _move_legacy_contents(source: Path, destination: Path) -> None:
    if not source.is_dir() or source.resolve() == destination.resolve():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if target.exists():
            if item.is_dir() and target.is_dir():
                _move_legacy_contents(item, target)
                continue
            raise RuntimeError(f"Cannot migrate {item}: destination already exists at {target}")
        shutil.move(str(item), str(target))


for _old_name, _new_dir in (
    ("data", DATA_DIR),
    ("outputs", OUTPUTS_DIR),
    ("logs", LOGS_DIR),
    (".cache", CACHE_DIR),
):
    _move_legacy_contents(RUNTIME_ROOT / _old_name, _new_dir)
_move_legacy_contents(
    RUNTIME_ROOT / "models" / "tts" / "_description_tokenizer_cache",
    CACHE_DIR / "tts" / "description_tokenizer",
)

for _d in (OUTPUTS_DIR, CACHE_DIR, LOGS_DIR, DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"

LOG_FILE = LOGS_DIR / "app.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", APP_CONFIG.get("log_level", "INFO")).upper()

_FFMPEG_CONFIG = MODELS_CONFIG.get("third_party", {}).get("ffmpeg", {})
FFMPEG_RUNTIME_ENABLED = bool(_FFMPEG_CONFIG.get("enabled", False))
FFMPEG_RUNTIME_DIR = MODELS_DIR / _FFMPEG_CONFIG["path"] if _FFMPEG_CONFIG.get("path") else None
FFMPEG_EXE = str(FFMPEG_RUNTIME_DIR / _FFMPEG_CONFIG["ffmpeg_executable"]) if FFMPEG_RUNTIME_DIR else None
FFPROBE_EXE = str(FFMPEG_RUNTIME_DIR / _FFMPEG_CONFIG["ffprobe_executable"]) if FFMPEG_RUNTIME_DIR else None
FFPLAY_EXE = str(FFMPEG_RUNTIME_DIR / _FFMPEG_CONFIG["ffplay_executable"]) if FFMPEG_RUNTIME_DIR else None

_CPU_COUNT = os.cpu_count() or 4
# How many translation jobs may run at the same time.
MAX_CONCURRENT_JOBS = max(1, int(os.environ.get("MAX_CONCURRENT_JOBS", str(APP_CONFIG.get("max_concurrent_jobs", 5)))))
MAX_PARALLEL_TRANSLATION_JOBS = max(
    1, int(os.environ.get("MAX_PARALLEL_TRANSLATION_JOBS", str(APP_CONFIG.get("max_parallel_translation_jobs", 3))))
)

ASR_MODEL = _active_model("asr", "english")
INDIC_ASR_MODEL = _active_model("asr", "indic")
ASR_PROVIDER = ASR_MODEL["engine"]
INDIC_ASR_PROVIDER = INDIC_ASR_MODEL["engine"]
ASR_MODEL_DIR = ASR_MODEL["path"]
ASR_COMPUTE_TYPE = ASR_MODEL.get("compute_type", "int8")
ASR_MODEL_ID = ASR_MODEL["model_id"]
ASR_MODEL_ESTIMATED_SIZE_GB = float(ASR_MODEL["estimated_size_gb"])
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
INDIC_ASR_MODEL_DIR = INDIC_ASR_MODEL["path"]
INDIC_ASR_MODEL_ID = INDIC_ASR_MODEL["model_id"]
INDIC_ASR_MODEL_ESTIMATED_SIZE_GB = float(INDIC_ASR_MODEL["estimated_size_gb"])
# Whisper remains the transcript authority. Per-segment IndicConformer output
# can truncate words at segment edges and should be enabled only for a source
# language where it has been evaluated against the actual media.
INDIC_ASR_ENABLED = bool(MODELS_CONFIG["asr"]["indic"].get("enabled", True))
# "ctc" (fast, default) or "rnnt" (also fast on CPU via ONNX, occasionally
# more accurate on tricky audio).
INDIC_ASR_DECODING = INDIC_ASR_MODEL.get("decoding", "ctc")
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

TRANSLATION_CONTEXT_ENABLED = os.environ.get("TRANSLATION_CONTEXT_ENABLED", "true").strip().lower() in ("1", "true", "yes")
TRANSLATION_CONTEXT_MAX_CHARS = max(100, int(os.environ.get("TRANSLATION_CONTEXT_MAX_CHARS", "1200")))
TRANSLATION_CONTEXT_MAX_DURATION_SECONDS = max(1.0, float(os.environ.get("TRANSLATION_CONTEXT_MAX_DURATION_SECONDS", "30")))
TRANSLATION_CONTEXT_MAX_SOURCE_TOKENS = max(32, int(os.environ.get("TRANSLATION_CONTEXT_MAX_SOURCE_TOKENS", "192")))
DOMAIN_PACK_ENABLED = os.environ.get("DOMAIN_PACK_ENABLED", "true").strip().lower() in ("1", "true", "yes")
ACTIVE_DOMAIN_PACK_PATH = Path(os.environ.get("ACTIVE_DOMAIN_PACK_PATH", str(BASE_DIR / "domains" / "agriculture" / "knowledge.json")))

TRANSLATION_EN_TO_INDIC_MODEL = _active_model("translation", "en_to_indic")
TRANSLATION_INDIC_TO_INDIC_MODEL = _active_model("translation", "indic_to_indic")
TRANSLATION_INDIC_TO_EN_MODEL = _active_model("translation", "indic_to_en")
TRANSLATION_MODEL_DIR = TRANSLATION_EN_TO_INDIC_MODEL["path"]
TRANSLATION_INDIC_INDIC_MODEL_DIR = TRANSLATION_INDIC_TO_INDIC_MODEL["path"]
TRANSLATION_INDIC_EN_MODEL_DIR = TRANSLATION_INDIC_TO_EN_MODEL["path"]
TRANSLATION_MODEL_ID = TRANSLATION_EN_TO_INDIC_MODEL["model_id"]
TRANSLATION_MODEL_ESTIMATED_SIZE_GB = float(TRANSLATION_EN_TO_INDIC_MODEL["estimated_size_gb"])
TRANSLATION_INDIC_INDIC_MODEL_ID = TRANSLATION_INDIC_TO_INDIC_MODEL["model_id"]
TRANSLATION_INDIC_INDIC_MODEL_ESTIMATED_SIZE_GB = float(TRANSLATION_INDIC_TO_INDIC_MODEL["estimated_size_gb"])
TRANSLATION_INDIC_EN_MODEL_ID = TRANSLATION_INDIC_TO_EN_MODEL["model_id"]
TRANSLATION_INDIC_EN_MODEL_ESTIMATED_SIZE_GB = float(TRANSLATION_INDIC_TO_EN_MODEL["estimated_size_gb"])
INDIC_TO_INDIC_USE_ENGLISH_PIVOT = bool(MODELS_CONFIG["translation"]["use_english_pivot"])

TTS_MODEL = _active_model("tts")
TTS_ENGINE = TTS_MODEL["engine"]
TTS_PIPER_ENGINE = MODELS_CONFIG["tts"]["models"]["piper"]["engine"]
TTS_MODEL_DIR = TTS_MODEL["path"]
TTS_MODEL_ID = TTS_MODEL["model_id"]
TTS_MODEL_ESTIMATED_SIZE_GB = float(TTS_MODEL["estimated_size_gb"])
# The TTS model's "description" (style prompt) tower reuses the flan-t5-large
# tokenizer. It is not bundled with the model, so it is fetched once from the
# Hugging Face Hub (tokenizer files only, a few MB) and cached here for
# fully-offline reuse afterwards.
TTS_DESCRIPTION_TOKENIZER_ID = MODELS_CONFIG["tts"]["description_tokenizer_id"]
TTS_DESCRIPTION_TOKENIZER_CACHE = CACHE_DIR / MODELS_CONFIG["tts"]["description_tokenizer_cache_directory"]

PIPER_VOICES_DIR = TTS_MODEL["path"]
# Language used for Piper synthesis when the target language has no dedicated
# Piper voice available (see app/models/piper_tts.py's voice table).
PIPER_DEFAULT_VOICE_LANG = MODELS_CONFIG["tts"]["default_piper_voice_language"]
PIPER_VOICE_BY_LANG = MODELS_CONFIG["tts"]["voice_by_language"]

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

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
ALLOWED_TEXT_EXTENSIONS = {".txt"}


@dataclass(frozen=True)
class Language:
    code: str  # short id used in UI + matched against whisper's detected language
    label: str
    flores_code: str  # IndicTrans2 / FLORES-200 tag
    tts_speakers: tuple[str, ...] | None = None


# Target languages: intersection of what IndicTrans2 (en->indic) and
# Indic Parler-TTS both support, plus English itself.
LANGUAGES: list[Language] = [
    Language(
        item["code"], item["label"], item["flores_code"],
        tuple(item["tts_speakers"]) if item["tts_speakers"] is not None else None,
    )
    for item in LANGUAGES_CONFIG["languages"]
]

LANGUAGES_BY_CODE = {lang.code: lang for lang in LANGUAGES}

INDIC_ASR_SUPPORTED_SOURCE_CODES = {
    item["code"] for item in LANGUAGES_CONFIG["languages"] if item["asr_provider"] == INDIC_ASR_PROVIDER
}
ASR_PROVIDER_BY_LANGUAGE = {item["code"]: item["asr_provider"] for item in LANGUAGES_CONFIG["languages"]}
INDIC_ASR_LANGUAGE_CODE_OVERRIDES = LANGUAGES_CONFIG.get("asr_model_code_overrides", {})

# Languages faster-whisper (OpenAI Whisper) can reliably transcribe. Several
# very low-resource Indic languages above (Bodo, Dogri, Konkani, Maithili,
# Manipuri, Santali, Odia) are NOT in Whisper's training set, so they cannot
# be used as *source* audio language, only as *target* dub languages.
WHISPER_SUPPORTED_SOURCE_CODES = {
    item["code"] for item in LANGUAGES_CONFIG["languages"] if item["whisper_supported"]
}
