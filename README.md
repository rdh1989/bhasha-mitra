# Bhasha Mitra - AI Video Dubbing (local, CPU-only)

A local web app that dubs videos into another language using only the
models already present in `models/`:

| Stage        | Model                                                        |
|--------------|---------------------------------------------------------------|
| Speech-to-text (segmentation + language ID) | `models/asr/faster_whisper/{tiny,small,medium}` (faster-whisper / CTranslate2) |
| Speech-to-text (Indic transcript refinement) | `models/asr/indic-conformer-600m-multilingual` (AI4Bharat IndicConformer, ONNX) |
| Translation (English → Indic) | `models/translation/indictrans2-en-indic-1B` |
| Translation (Indic → Indic) | `models/translation/indictrans2-indic-indic-1B` |
| Translation (Indic → English) | `models/translation/indictrans2-indic-en-1B` |
| Text-to-speech | `models/tts/piper-voices` (Piper, default) |

Everything runs on CPU. Videos are never uploaded/copied - you submit the
local path of an already-present video file and the app reads it directly
from disk. The web UI (FastAPI) has:

- **Dashboard** - submit one or more local video paths at once (each becomes
  its own job, processed in parallel up to a configurable limit), live
  stats, and a live-refreshing recent-jobs table.
- **Job History** - every job ever run, persisted in a local SQLite database,
  filterable by status, with per-job log/error details and downloads.
- **User Administration** (admin only) - add/edit/disable/delete local
  accounts with one of three roles.
- **About** / **Help & Support** - self-service documentation built into the app.

### Roles

| Role | Can do |
|---|---|
| `admin` | Everything: submit jobs, view history, manage users. |
| `operator` | Submit jobs and view history. No user administration. |
| `user` | Read-only: view the dashboard and job history only. |

All users and all job history are stored in `data/app.db` (SQLite).

## Translation routing

Three IndicTrans2 checkpoints are used depending on the source/target
language pair, so translation is always direct - no pivoting through an
intermediate language, and no double-translation quality loss:

- **source language == target language** → transcript is used as-is, no
  translation step.
- **source == English** → the en-indic model translates English → target
  Indic language directly.
- **source and target are both Indic (and different)**, e.g. Marathi → Hindi
  → the indic-indic model translates directly, without pivoting through
  English (this used to go through a lossy English pivot and produced poor
  quality translations - it no longer does).
- **target == English** (source is a non-English Indic language) → the
  indic-en model translates the already-transcribed source segments directly
  to English (this used to rely on Whisper's own, less reliable,
  speech-to-English `task=translate` pass - it no longer does, so this case
  is also faster now since it skips a second full ASR pass).

Source language is auto-detected by Whisper; only a handful of low-resource
Indic languages (Bodo, Dogri, Konkani, Maithili, Manipuri, Santali, Odia)
are not in Whisper's training data and therefore cannot be used as
**source** audio (they can still be selected as dub **targets**).

## Higher-quality Indic transcripts

Whisper is only used for fast segmentation and language detection. When the
detected source language is one of the 22 languages AI4Bharat's
IndicConformer supports, each Whisper-timed clip is re-transcribed with that
specialized model instead - it's ONNX-based (fast on CPU) and produces more
accurate, native-script text than Whisper's general-purpose decoder for
Indic speech, which then also improves translation quality downstream (better
input in, better translation out). Falls back to Whisper's own text per
segment (or entirely) if IndicConformer fails, or is disabled via
`INDIC_ASR_ENABLED=false`.

## Windows Prerequisites

### Supported environment

The current working environment is Windows 11 x64 with CPython 3.13.9 and
64-bit AMD64 Python. Use 64-bit Windows and 64-bit Python; the exact minimum
Windows release and minimum CPU model were not independently verified. The
application is configured for CPU execution: `torch==2.13.0+cpu`, the CPU
`onnxruntime` package, and CTranslate2 `int8` ASR by default. A CUDA GPU and
NVIDIA driver are not required by the current setup.

Python package installation requires internet access (or an internal package
mirror). Runtime does not call a cloud API and is intended to work offline
once the local model assets are present. The repository's model directories
must be copied or checked out separately if they are not included in the clone.

### Microsoft Visual C++ Redistributable

The native Windows wheels used by Torch and related packages contain compiled
extensions but do not bundle every Microsoft C/C++ runtime DLL. The current
machine has the Microsoft Visual C++ 2015-2022 x64 Redistributable, reported as
version `14.51.36247`. This is evidence for the required runtime generation,
not a verified minimum version. Exact minimum version not verified; install
the currently supported Microsoft Visual C++ Redistributable for Visual Studio
2015-2022, x64, from Microsoft's official download page:
<https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist>.

This runtime is needed to run the source-installed native wheels, especially
Torch/CTranslate2. Visual Studio Build Tools are **not required to run** the
current application or to install the available wheels. They are only needed
if pip cannot use a compatible wheel and must compile a native package from
source, or when developing native extensions. `build.py` separately copies
the build machine's MSVC DLLs into a PyInstaller distribution when those DLLs
are available; that does not remove the source-environment prerequisite.

Check a machine before installing:

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' |
  Where-Object { $_.DisplayName -like '*Visual C++*Redistributable*' } |
  Select-Object DisplayName, DisplayVersion
where.exe vcruntime140.dll
where.exe msvcp140.dll
```

The `where.exe` commands can be empty even when the runtime is registered;
registry evidence and a successful Torch import are more useful checks.

### FFmpeg

No separate system-wide FFmpeg installation is required. The application first
uses the repository-provided `models/third_party/ffmpeg/*/bin/ffmpeg.exe` when
present. If that directory is absent, it falls back to the FFmpeg executable
bundled by `imageio-ffmpeg==0.6.0`. `ffprobe.exe` is also present in the
repository-provided build, but application media operations invoke FFmpeg.

### Git

Git is required to clone the repository. It is not a Python runtime dependency.

## Clean Windows setup

1. Install 64-bit CPython 3.13, the supported Microsoft VC++ Redistributable,
   and Git.
2. Clone the repository and open PowerShell in its root directory.
3. Create and activate the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The CPU Torch pin is `torch==2.13.0+cpu`. If the configured package index
cannot resolve that local-version wheel, install from the official PyTorch CPU
index before installing the remaining requirements:

```powershell
python -m pip install torch==2.13.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

4. Ensure the local model assets exist under `models/`:

```text
models/asr/faster_whisper/medium/
models/asr/indic-conformer-600m-multilingual/
models/translation/indictrans2-en-indic-1B/
models/translation/indictrans2-indic-indic-1B/
models/translation/indictrans2-indic-en-1B/
models/tts/piper-voices/
```

Python packages and AI model files are separate dependencies. Model files are
not installed by pip and are not listed in `requirements.txt`. The default
configuration expects the paths above and does not download these models at
runtime. `INDIC_ASR_ENABLED=false` is the current default; the IndicConformer
files are still required when that refinement is enabled.

5. Verify the installation without loading model weights:

```powershell
python -m pip check
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda)"
python -c "import fastapi, numpy, onnxruntime, soundfile, transformers; print(fastapi.__version__); print(numpy.__version__); print(onnxruntime.__version__); print(soundfile.__version__); print(transformers.__version__)"
python -c "import app.main, launcher; print('Bhasha Mitra imports OK')"
```

6. Start the development server:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Startup loads the configured local models and can take several minutes. Open
`http://localhost:8000`. Runtime does not require internet for the default
Piper path, but package installation and acquisition of missing model assets
do require access to the relevant sources.

## Dependency roles

`requirements.txt` contains exact versions for application runtime packages
and the PyInstaller build tools used by `build.py`. The tests use Python's
standard-library `unittest`; pytest is not part of the current environment.
Standard-library modules such as SQLite, pathlib, threading, and subprocess
are intentionally not listed. TensorBoard, OCR packages, GPU runtimes,
Parler-TTS, and unrelated installed packages are intentionally excluded.

The default TTS backend is Piper. The older Parler backend is conditional and
is not reproducible from the normal requirements file because the current
installation was made from Git with `--no-deps`; its training-only declared
dependencies are not used by the default application path.

## Windows troubleshooting

### DLL load failed or WinError 1114

First verify 64-bit Python, `torch==2.13.0+cpu`, and the x64 VC++
Redistributable. Check `python -c "import torch; print(torch.__version__)"`.
If that fails, inspect the missing DLL named by the traceback and reinstall
the supported x64 VC++ Redistributable. A CPU without the AVX2 capability used
by the current Torch wheel is another possible hardware limitation; this was
not solved by changing Python dependencies.

### Torch or ONNX Runtime import failure

Confirm that `python -m pip --version` points into `.venv`, that Python is
64-bit, and that `python -m pip check` reports no broken requirements. This
project uses `onnxruntime`, not `onnxruntime-gpu`; do not substitute the GPU
package. Recreate the venv only after preserving the reported error, since
changing package versions would no longer reproduce the current environment.

### FFmpeg not found

Confirm `models/third_party/ffmpeg/*/bin/ffmpeg.exe` exists. If it does not,
verify that `imageio-ffmpeg` is installed and that
`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"`
returns an executable path. A separate FFmpeg installation is not required.

## Run

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application attempts to preload ASR, translation, Indic ASR, and TTS
engines at startup. Model loading can take 20s-1min+ depending on your CPU
and available memory. Individual preload failures are logged and do not
necessarily prevent the server from starting; the affected model may fail
again when a job needs it. Successfully loaded engines are reused by jobs
instead of being reloaded for every request.

Open http://localhost:8000 and sign in with `admin` / `admin` (this seeds a
one-time default admin account in the SQLite database on first run - manage
or change it from the User Administration page, or override the seed via the
`APP_USERNAME` / `APP_PASSWORD` environment variables before the first run).

## Output files

Job submission takes an absolute local file path (one per line for multiple
jobs) instead of an upload - the source video is read in place and never
copied. Every job writes its intermediate and final files under:

```
outputs/<video-file-stem>/<job-id>/
  audio.wav             # extracted source audio
  transcript.json        # source-language segments (start, end, text) after ASR
  translation.json       # translated segments (start, end, text) used for TTS/subtitles
  segments/              # per-segment synthesized/time-stretched TTS clips
  dubbed_audio.wav       # full assembled dubbed track
  subtitles.srt           # translated-text captions, timed to each dubbed segment
  <job-id>.mp4           # final output: original video + dubbed audio + embedded subtitle track
```

Subtitles are generated from the same (start, end, text) segments used to
place the dubbed audio, so captions stay in sync with what's spoken. Each
segment is its own subtitle cue (wrapped to at most 2 short lines) that only
appears during its own time window - never one giant caption spanning the
whole video. They're embedded as a soft/selectable subtitle track (`mov_text`)
in the output MP4, so no video re-encoding is needed and the track can be
toggled on/off in players that support it.

The `outputs/<video-file-stem>/` folder is reused (not recreated) across
multiple runs of the same source video - each run just gets its own
`<job-id>` subfolder underneath it.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `ASR_MODEL_SIZE` | `small` | `tiny` / `small` / `medium` faster-whisper model to use |
| `ASR_COMPUTE_TYPE` | `int8` | CTranslate2 compute type (int8 is fastest on CPU) |
| `MAX_CONCURRENT_JOBS` | `5` | Max number of translation jobs processed in parallel |
| `ASR_CPU_THREADS` | all cores | CPU threads faster-whisper uses per job |
| `ASR_NUM_WORKERS` | `MAX_CONCURRENT_JOBS` | Concurrent transcribe() calls CTranslate2 can serve on the shared ASR model |
| `TORCH_NUM_THREADS` | all cores | Global PyTorch intra-op thread cap (translation + TTS models) |
| `INDIC_ASR_ENABLED` | `true` | Re-transcribe Indic-language segments with IndicConformer for higher quality |
| `INDIC_ASR_DECODING` | `ctc` | `ctc` (fast) or `rnnt` decoding strategy for IndicConformer |
| `TRANSLATION_MODEL_SIZE` | `1B` | `1B` for the best observed speed and translation quality, or `dist` for a smaller memory footprint |
| `APP_USERNAME` / `APP_PASSWORD` | `admin` / `admin` | Login credentials |
| `SESSION_SECRET` | random per process restart | Set a fixed value to keep sessions alive across restarts |

## Notes on quality / performance

- CPU inference is slow: expect several minutes of processing per minute of
  video, dominated by `medium` ASR and the TTS pass. Use `ASR_MODEL_SIZE=small`
  or `tiny` for faster (less accurate) transcription.
- Dubbed speech is time-stretched per sentence/segment to roughly fit the
  original segment's duration (via ffmpeg `atempo`) for reasonable sync; this
  is not frame-accurate lip-sync.
- Up to `MAX_CONCURRENT_JOBS` (default 5) jobs run in parallel, all reusing
  the same models loaded once at startup - no reloading happens per job.
  `ASR_CPU_THREADS` and `TORCH_NUM_THREADS` default to **all** CPU cores so a
  single job isn't artificially slowed down (the common case). If you
  routinely run several heavy jobs at the exact same time on a low-core
  machine, lower these explicitly (e.g. cores ÷ `MAX_CONCURRENT_JOBS`) to
  avoid oversubscription - that trades slower individual jobs for higher
  total throughput when many run at once.
- TTS generation length is capped based on the input text (rather than the
  model's default ~30s ceiling) to avoid occasional runaway generations, but
  CPU autoregressive decoding is still the slowest step by far - expect on
  the order of 10-20x realtime (a few seconds of dubbed speech can take a
  minute or more), even with all cores available.
  `MAX_CONCURRENT_JOBS` if you have fewer than ~5-10 CPU cores.
