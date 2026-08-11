from ai.pipeline.dubbing_pipeline import DubbingPipeline


def test_apply_edge_fade_reduces_boundary_click() -> None:
    pipeline = DubbingPipeline(tts_service=None)  # type: ignore[arg-type]

    # 4 mono PCM16 samples with abrupt full-scale start and end.
    # Little-endian int16: [32767, 32767, 32767, 32767]
    abrupt = b"\xff\x7f\xff\x7f\xff\x7f\xff\x7f"

    faded = pipeline._apply_edge_fade(
        frames=abrupt,
        channels=1,
        sample_rate=1000,
    )

    # First and last sample must be lower than full scale after fade.
    assert faded[:2] != b"\xff\x7f"
    assert faded[-2:] != b"\xff\x7f"


def test_mix_pcm16_saturates() -> None:
    pipeline = DubbingPipeline(tts_service=None)  # type: ignore[arg-type]

    # 30000 + 30000 should saturate at 32767.
    dst = (30000).to_bytes(2, "little", signed=True)
    src = (30000).to_bytes(2, "little", signed=True)

    mixed = pipeline._mix_pcm16(dst, src)
    value = int.from_bytes(mixed[:2], "little", signed=True)

    assert value == 32767


def test_resize_audio_linear_interpolation() -> None:
    pipeline = DubbingPipeline(tts_service=None)  # type: ignore[arg-type]

    # mono samples [0, 10000]
    frames = (
        (0).to_bytes(2, "little", signed=True)
        + (10000).to_bytes(2, "little", signed=True)
    )

    resized = pipeline._resize_audio(
        frames=frames,
        current_frames=2,
        target_frames=3,
        channels=1,
    )

    middle = int.from_bytes(resized[2:4], "little", signed=True)

    # Linear interpolation should create midpoint around 5000.
    assert 4500 <= middle <= 5500
