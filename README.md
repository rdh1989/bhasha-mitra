# 🚀 Bhasha Mitra

## Overview

Bhasha Mitra is an offline AI-powered multilingual video translation platform.

It enables users to translate videos into multiple Indian languages while preserving subtitles and supporting future AI providers through a configurable plugin architecture.

---

## Features

- Offline First
- Modular Architecture
- Provider Based AI Integration
- Dynamic Model Loading
- REST API
- Background Job Processing
- Multi-language Support
- Subtitle Generation
- Speech-to-Text
- Text Translation
- Text-to-Speech
- Plugin Support
- Configuration Driven

---

## Technology Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- FFmpeg
- Faster-Whisper
- IndicTrans2
- YAML Configuration

---

## Project Structure

```
app/
domain/
ai/
pipelines/
workers/
infrastructure/
plugins/
frontend/
storage/
config/
tests/
docs/
```

---

## Development

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run application

```bash
python launcher.py
```

Swagger

```
http://localhost:8000/docs
```

---

## License

MIT License