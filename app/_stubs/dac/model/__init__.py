"""Placeholder for the optional `dac` (descript-audio-codec) package.

parler_tts/__init__.py unconditionally does `from .dac_wrapper import DACConfig,
DACModel`, whose modeling_dac.py in turn does `from dac.model import DAC`. That
class is only ever *instantiated* for audio codecs registered under the legacy
"dac" config name; our transformers version (>4.44.2) makes parler_tts register
its wrapper under "dac_on_the_hub" instead, and Indic Parler-TTS's own
audio_encoder config is model_type="dac", which resolves to transformers' own
built-in `DacModel` (no external `dac` package involved). So `DAC` here is only
needed to satisfy the import statement - it is never actually used.
"""


class DAC:  # pragma: no cover - intentionally inert, see module docstring
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "This is a stub for the unused 'dac' package. Indic Parler-TTS uses "
            "transformers' built-in DacModel instead."
        )
