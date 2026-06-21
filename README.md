# <img src="assets/logo/logo.png" width="60" alt="Bhasha Mitra Logo"> Bhasha Mitra

### One India. Many Languages.

Offline AI-powered video translation platform designed to make multilingual content accessible across Indian languages without internet connectivity.

---

## Vision

Bhasha Mitra enables users to translate video content into regional Indian languages using a completely offline and lightweight AI pipeline.

The platform is designed for:

* Offline operation
* CPU-only inference
* Plug-and-play deployment
* LAN accessibility
* Multi-language expansion

---

## MVP Features

### Release 1.0

* English → Marathi Translation
* Speech Recognition (ASR)
* Subtitle Generation (SRT/VTT)
* Transcript Generation
* Local Web UI
* LAN Access
* Single EXE Deployment
* Offline Processing

---

## User Workflow

```text
Insert Pen Drive
        ↓
Run BhashaMitra.exe
        ↓
Browser Opens
        ↓
Upload Video
        ↓
Translate
        ↓
Download Marathi Subtitles
```

---

## High Level Architecture

```text
Video
  ↓
Audio Extraction
  ↓
Speech Recognition
  ↓
English Transcript
  ↓
Translation
  ↓
Marathi Text
  ↓
Subtitle Generation
  ↓
Output Files
```

---

## Technology Stack

| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| Backend          | FastAPI                             |
| Frontend         | HTML, CSS, JavaScript               |
| ASR              | Whisper Tiny                        |
| Translation      | Quantized Offline Translation Model |
| Video Processing | FFmpeg                              |
| Packaging        | PyInstaller                         |
| Deployment       | Single EXE                          |

---

## Repository Structure

```text
bhasha_mitra/

├── app/
│   ├── api/
│   └── ui/
│
├── assets/
│
├── models/
│
├── logs/
│
├── output/
│
├── launcher.py
│
└── requirements.txt
```

---

## Resource Targets

| Metric          | Target          |
| --------------- | --------------- |
| Package Size    | < 2 GB          |
| Application RAM | < 2 GB          |
| Runtime         | CPU Only        |
| Internet        | Not Required    |
| Installation    | None            |
| Access          | Localhost + LAN |

---

## Development Roadmap

### Phase 1

* UI Framework
* Dashboard
* Upload Page
* Settings Page

### Phase 2

* Video Upload APIs
* Job Tracking

### Phase 3

* FFmpeg Integration
* Audio Extraction

### Phase 4

* Whisper Integration

### Phase 5

* Translation Engine

### Phase 6

* Subtitle Generation

### Phase 7

* EXE Packaging

---

## Future Releases

### Version 2

* Marathi Voice Dubbing
* Timestamp Optimization
* Speaker Identification

### Version 3

* Hindi Support
* Gujarati Support
* Kannada Support
* Tamil Support

### Version 4

* Live Translation
* Streaming Support
* GPU Acceleration

---

## Architecture Decisions

* Modular Monolith Architecture
* Layered Design
* Service Pattern
* Pipeline Pattern
* Repository Pattern
* Single Repository Strategy

---

## Tagline

**Bhasha Mitra — One India. Many Languages.**
