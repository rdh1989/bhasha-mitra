# Bhasha Mitra Voice Cloning Module

This is a **separate TTS path** for voice-preserving dubbing.

## Existing TTS is untouched

The existing:

- `ai/tts`
- Piper provider
- `TTSService`
- `TTSPipeline`

are not modified by this module.

## Model

Initial provider: **IndicF5**.

IndicF5 supports Marathi and uses:

1. target text
2. reference audio
3. transcript of the reference audio

to condition the generated speech on the reference speaker.

## Request

```python
VoiceCloneRequest(
    text="मराठीमध्ये भाषांतरित मजकूर",
    language="mr",
    reference_audio_path=Path("reference.wav"),
    reference_text="This is the exact English transcript of reference.wav.",
    output_path=Path("dubbed.wav"),
)
```

## Reference audio rules

For the first prototype, use a clean speech-only reference clip of roughly 5–10 seconds.

The `reference_text` must match that clip exactly.

Do not use music, multiple speakers, or overlapping speech in the reference.

## Offline requirement

The model must be downloaded and placed locally before deployment.

The provider uses:

```python
local_files_only=True
```

so runtime inference does not intentionally download the model.

## Important

The model's reference conditioning is intended to preserve speaker characteristics and prosody. It should be evaluated on the actual Bhasha Mitra English→Marathi videos before being considered production-ready.

Voice cloning should only be used when the speaker's permission has been obtained.
