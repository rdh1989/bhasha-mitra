"""IndicTrans2 English -> Indic translation wrapper.

Important: the bundled checkpoint (indictrans2-en-indic-dist-200M) only
translates FROM English INTO Indic languages. It cannot translate between
two Indic languages or from an Indic language into English. The pipeline
(see app/pipeline.py) works around this by using faster-whisper's own
speech-to-English "translate" task as a pivot when the source audio is not
English.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class TranslationEngine:
    def __init__(self, model_dir):
        self._model_dir = str(model_dir)
        self._model = None
        self._tokenizer = None
        self._processor = None
        self._lock = threading.Lock()

    def ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            logger.info("Loading IndicTrans2 translation model from %s", self._model_dir)
            try:
                import torch
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                from IndicTransToolkit.processor import IndicProcessor

                self._tokenizer = AutoTokenizer.from_pretrained(self._model_dir, trust_remote_code=True)
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    self._model_dir, trust_remote_code=True, torch_dtype=torch.float32
                )
                model.eval()
                self._model = model
                self._processor = IndicProcessor(inference=True)
            except Exception:
                logger.exception("Failed to load translation model from %s", self._model_dir)
                raise
            logger.info("Translation model loaded successfully")

    def unload(self) -> None:
        """Release the model/tokenizer/processor so their memory can be freed."""
        with self._lock:
            if self._model is None:
                return
            self._model = None
            self._tokenizer = None
            self._processor = None
        logger.info("Translation model unloaded")

    def translate(self, texts: list[str], tgt_lang: str, src_lang: str = "eng_Latn") -> list[str]:
        if not texts:
            return []
        self.ensure_loaded()
        import torch

        logger.debug("Translating %d segment(s): %s -> %s", len(texts), src_lang, tgt_lang)
        try:
            batch = self._processor.preprocess_batch(texts, src_lang=src_lang, tgt_lang=tgt_lang)
            inputs = self._tokenizer(
                batch,
                truncation=True,
                padding="longest",
                return_tensors="pt",
                return_attention_mask=True,
            )
            with torch.no_grad():
                generated = self._model.generate(
                    **inputs,
                    use_cache=True,
                    min_length=0,
                    max_length=256,
                    num_beams=5,
                    num_return_sequences=1,
                )
            decoded = self._tokenizer.batch_decode(
                generated, skip_special_tokens=True, clean_up_tokenization_spaces=True
            )
            result = self._processor.postprocess_batch(decoded, lang=tgt_lang)
        except Exception:
            logger.exception("Translation failed (%s -> %s)", src_lang, tgt_lang)
            raise
        logger.info("Translated %d segment(s): %s -> %s", len(texts), src_lang, tgt_lang)
        return result
