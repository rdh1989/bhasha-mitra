"""
===============================================================================
Bhasha Mitra - NLLB Framework Validation
-------------------------------------------------------------------------------
Purpose:
    Validate NLLB model loading and translation inference.
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
    print("NLLB FRAMEWORK VALIDATION")
    print("=" * 80)

    #
    # Import
    #
    print("\n[1/5] Importing ModelManager...")

    from ai.model_manager.manager import ModelManager

    print("PASS")

    #
    # Create Manager
    #
    print("\n[2/5] Creating ModelManager...")

    manager = ModelManager()

    print("PASS")

    #
    # Initialize Framework
    #
    print("\n[3/5] Initializing Framework...")

    manager.initialize()

    print("PASS")

    #
    # Load Model
    #
    print("\n[4/5] Loading NLLB Model...")

    translation = manager.load_model(
        category="translation",
        model="NLLB-600M",
    )

    model = translation["model"]
    tokenizer = translation["tokenizer"]

    print("PASS")

    #
    # Translation Test
    #
    print("\n[5/5] Running Translation...")

    english = "Welcome to Bhasha Mitra"

    print("\nInput")
    print("-" * 80)
    print(english)

    #
    # NLLB Language Codes
    #
    src_lang = "eng_Latn"
    tgt_lang = "mar_Deva"

    tokenizer.src_lang = src_lang

    inputs = tokenizer(
        english,
        return_tensors="pt",
    )

    with torch.no_grad():

        generated = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(
                tgt_lang
            ),
            max_length=256,
        )

    translated = tokenizer.batch_decode(
        generated,
        skip_special_tokens=True,
    )[0]

    print("\nOutput")
    print("-" * 80)
    print(translated)

    print("\n" + "=" * 80)
    print("NLLB FRAMEWORK VALIDATION PASSED")
    print("=" * 80)

except Exception as exc:

    print("\n" + "=" * 80)
    print("FRAMEWORK VALIDATION FAILED")
    print("=" * 80)

    print(type(exc).__name__)
    print(exc)
    print()

    traceback.print_exc()