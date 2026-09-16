import threading
import unittest
from unittest.mock import patch

import torch

from app.models.translate import TranslationEngine


class FakeProcessor:
    def preprocess_batch(self, texts, **_kwargs):
        return texts

    def postprocess_batch(self, decoded, **_kwargs):
        return decoded


class FakeTokenizer:
    def __init__(self, input_ids=None, attention_mask=None):
        self.input_ids = input_ids
        self.attention_mask = attention_mask

    def __call__(self, _batch, **_kwargs):
        result = {"input_ids": self.input_ids}
        if self.attention_mask is not None:
            result["attention_mask"] = self.attention_mask
        return result

    def batch_decode(self, generated, **_kwargs):
        return [f"translation-{index}" for index in range(generated.shape[0])]


class FakeModel:
    def generate(self, **inputs):
        if inputs["input_ids"].numel() == 0:
            return torch.zeros((1, 1), dtype=torch.long)
        return inputs["input_ids"]


class TranslationTensorRegressionTests(unittest.TestCase):
    def make_engine(self, input_ids, attention_mask):
        engine = TranslationEngine.__new__(TranslationEngine)
        engine._model = FakeModel()
        engine._tokenizer = FakeTokenizer(input_ids, attention_mask)
        engine._processor = FakeProcessor()
        engine._inference_lock = threading.Lock()
        return engine

    def test_multi_item_tensor_uses_attention_mask_without_boolean_error(self):
        input_ids = torch.tensor([[1, 2, 3, 0], [1, 2, 3, 4]])
        attention_mask = torch.tensor([[1, 1, 1, 0], [1, 1, 1, 1]])
        engine = self.make_engine(input_ids, attention_mask)
        with patch.object(TranslationEngine, "ensure_loaded"):
            result = engine.translate(["one", "two"], "hin_Deva", "mar_Deva")
        self.assertEqual(len(result), 2)

    def test_empty_tensor_is_safe(self):
        engine = self.make_engine(torch.empty((0, 0), dtype=torch.long), torch.empty((0, 0), dtype=torch.long))
        with patch.object(TranslationEngine, "ensure_loaded"):
            result = engine.translate(["one"], "hin_Deva", "mar_Deva")
        self.assertEqual(len(result), 1)

    def test_single_item_tensor_is_safe(self):
        engine = self.make_engine(torch.tensor([[1, 2]]), torch.tensor([[1, 1]]))
        with patch.object(TranslationEngine, "ensure_loaded"):
            result = engine.translate(["one"], "hin_Deva", "mar_Deva")
        self.assertEqual(len(result), 1)

    def test_missing_attention_mask_uses_tensor_shape(self):
        engine = self.make_engine(torch.tensor([[1, 2, 3]]), None)
        with patch.object(TranslationEngine, "ensure_loaded"):
            result = engine.translate(["one"], "hin_Deva", "mar_Deva")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
