import unittest

import numpy as np

from app.ai.alignment.indic_ctc_aligner import _group_words, _tokenize_text, _viterbi_spans


class IndicCtcAlignerTests(unittest.TestCase):
    def test_tokenizer_uses_sentencepiece_word_markers(self):
        vocab = ["<unk>", "▁शे", "ळी", "▁क", "ि", "ं", "|"]
        token_ids = {token: index for index, token in enumerate(vocab)}
        labels, unknown = _tokenize_text("शेळी किं", token_ids, vocab, 6)
        self.assertEqual(unknown, [])
        self.assertEqual([vocab[index] for index in labels], ["▁शे", "ळी", "▁क", "ि", "ं"])

    def test_viterbi_and_word_grouping_are_monotonic(self):
        blank = 4
        labels = [1, 2, 3]
        path = [blank, 1, 1, blank, 2, blank, 3, 3, blank]
        logits = np.full((len(path), 5), -10.0)
        for frame, label in enumerate(path):
            logits[frame, label] = 0.0
        spans, _ = _viterbi_spans(logits, labels, blank)
        words = _group_words(spans, labels, ["<unk>", "▁शे", "ळी", "▁क", "|"], 10.0, 10.72, 0.08)
        self.assertEqual([word["text"] for word in words], ["शेळी", "क"])
        self.assertEqual([(word["start"], word["end"]) for word in words], [(10.08, 10.4), (10.48, 10.64)])


if __name__ == "__main__":
    unittest.main()
