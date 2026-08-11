from types import SimpleNamespace

from ai.translation.models import TranslationRequest
from ai.translation.service import TranslationService


class FakeTokenizer:
    def __init__(self):
        self.src_lang = None

    def __call__(self, text, **kwargs):
        return {"input_ids": [1, 2, 3]}

    def convert_tokens_to_ids(self, token):
        return 123

    def batch_decode(self, outputs, skip_special_tokens=True):
        return ["hola"]


class FakeModelBundle:
    def __init__(self):
        self.calls = []
        self.model = SimpleNamespace(generate=self._generate)
        self.tokenizer = FakeTokenizer()

    def __getitem__(self, key):
        if key == "model":
            return self.model
        if key == "tokenizer":
            return self.tokenizer
        raise KeyError(key)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        return [[1, 2, 3]]


class FakeModelManager:
    def __init__(self, bundle):
        self._bundle = bundle
        self.loaded = False

    def get_default_model(self, category):
        assert category == "translation"
        if not self.loaded:
            raise RuntimeError("Model 'translation:NLLB-600M' is not loaded.")
        return self._bundle

    def get_default_metadata(self, category):
        assert category == "translation"
        return {"model": "NLLB-600M"}

    def load_model(self, category, model):
        assert category == "translation"
        assert model == "NLLB-600M"
        self.loaded = True
        return self._bundle


def test_translate_uses_fast_generation_settings(monkeypatch):
    bundle = FakeModelBundle()
    manager = FakeModelManager(bundle)
    manager.loaded = True

    monkeypatch.setattr(
        "ai.translation.service.ModelManager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "ai.translation.service.NLLB_LANGUAGE_MAP",
        {"english": "eng_Latn", "spanish": "spa_Latn"},
    )

    service = TranslationService(adapter=None)
    result = service.translate(
        TranslationRequest(
            text="hello world",
            source_language="English",
            target_language="Spanish",
        )
    )

    assert result.translated_text == "hola"
    assert len(bundle.calls) == 1
    kwargs = bundle.calls[0]
    assert kwargs["max_new_tokens"] == 90
    assert kwargs["num_beams"] == 1
    assert kwargs["do_sample"] is False
    assert kwargs["repetition_penalty"] == 1.15
    assert kwargs["no_repeat_ngram_size"] == 3
    assert kwargs["length_penalty"] == 1.0


def test_translate_splits_long_input_into_chunks(monkeypatch):
    bundle = FakeModelBundle()
    manager = FakeModelManager(bundle)
    manager.loaded = True

    monkeypatch.setattr(
        "ai.translation.service.ModelManager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "ai.translation.service.NLLB_LANGUAGE_MAP",
        {"english": "eng_Latn", "spanish": "spa_Latn"},
    )

    service = TranslationService(adapter=None)
    long_text = "This is sentence one. " * 80
    result = service.translate(
        TranslationRequest(
            text=long_text,
            source_language="English",
            target_language="Spanish",
        )
    )

    assert result.translated_text.startswith("hola")
    assert len(bundle.calls) >= 2


def test_translate_lazy_loads_default_model(monkeypatch):
    bundle = FakeModelBundle()
    manager = FakeModelManager(bundle)

    monkeypatch.setattr(
        "ai.translation.service.ModelManager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "ai.translation.service.NLLB_LANGUAGE_MAP",
        {"english": "eng_Latn", "spanish": "spa_Latn"},
    )

    service = TranslationService(adapter=None)
    result = service.translate(
        TranslationRequest(
            text="hello world",
            source_language="English",
            target_language="Spanish",
        )
    )

    assert manager.loaded is True
    assert result.translated_text == "hola"
