"""
===============================================================================
Bhasha Mitra - IndicTrans2 Framework Validation
-------------------------------------------------------------------------------
Purpose:
    Validate IndicTrans2 model loading and translation inference.
===============================================================================
"""

from pathlib import Path
import sys
import traceback
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:

    print("=" * 80)
    print("INDICTRANS2 FRAMEWORK VALIDATION")
    print("=" * 80)

    print("\n[1/5] Importing ModelManager...")

    from ai.model_manager.manager import ModelManager
    from IndicTransToolkit.processor import IndicProcessor

    print("PASS")

    print("\n[2/5] Creating ModelManager...")

    manager = ModelManager()

    print("PASS")

    print("\n[3/5] Initializing Framework...")

    manager.initialize()

    print("PASS")

    print("\n[4/5] Loading IndicTrans2 Model...")

    translation = manager.load_model(
        category="translation",
        model="IndicTrans2",
    )

    model = translation["model"]
    tokenizer = translation["tokenizer"]

    print("PASS")

    print("\n[5/5] Running Translation...")

    processor = IndicProcessor(inference=True)

    english = "Welcome to Bhasha Mitra"

    print("\nInput")
    print("-" * 80)
    print(english)

    batch = processor.preprocess_batch(
        [english],
        src_lang="eng_Latn",
        tgt_lang="mar_Deva",
    )

    inputs = tokenizer(
        batch,
        truncation=True,
        padding="longest",
        return_tensors="pt",
        return_attention_mask=True,
    )

    with torch.no_grad():

        generated = model.generate(
            **inputs,
            use_cache=True,
            min_length=0,
            max_length=256,
            num_beams=5,
            num_return_sequences=1,
        )

    decoded = tokenizer.batch_decode(
        generated,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )

    translations = processor.postprocess_batch(
        decoded,
        lang="mar_Deva",
    )

    print("\nOutput")
    print("-" * 80)
    print(translations[0])

    print("\n" + "=" * 80)
    print("INDICTRANS2 FRAMEWORK VALIDATION PASSED")
    print("=" * 80)

except Exception as exc:

    print("\n" + "=" * 80)
    print("FRAMEWORK VALIDATION FAILED")
    print("=" * 80)

    print(type(exc).__name__)
    print(exc)
    print()

    traceback.print_exc()