"""
===============================================================================
Bhasha Mitra - Loaded Model Validation
-------------------------------------------------------------------------------
Purpose
-------
Validate that AI models have already been loaded by the AI Framework and can
be retrieved from the ModelManager cache.

Flow
----
1. Create ModelManager
2. Verify models are loaded
3. Get models from cache
4. Perform a simple translation

Prerequisite
------------
Application must already be running.
===============================================================================
"""

from pathlib import Path
import sys
import traceback
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def banner(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


try:

    banner("BHASHA MITRA - LOADED MODEL VALIDATION")

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    print("\n[1/4] Importing ModelManager...")

    from ai.model_manager.manager import ModelManager

    print("PASS")

    # ------------------------------------------------------------------
    # Get Manager
    # ------------------------------------------------------------------

    print("\n[2/4] Checking Loaded Models...")

    manager = ModelManager()

    print("\nLoaded Models")
    print("-" * 80)

    for model in manager.list_loaded_models():
        print(model)

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    required_models = [
        ("asr", "medium"),
        ("translation", "NLLB-600M"),
    ]

    for category, model in required_models:

        if not manager.is_loaded(category, model):
            raise RuntimeError(
                f"{category}:{model} is not loaded.\n"
                "Start Bhasha Mitra first."
            )

    print("\nPASS")

    # ------------------------------------------------------------------
    # Get Models
    # ------------------------------------------------------------------

    print("\n[3/4] Retrieving Models From Cache...")

    whisper = manager.get_model(
        category="asr",
        model="medium",
    )

    translation = manager.get_model(
        category="translation",
        model="NLLB-600M",
    )

    model = translation["model"]
    tokenizer = translation["tokenizer"]

    print("PASS")

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    print("\n[4/4] Running Translation...")

    tokenizer.src_lang = "eng_Latn"

    text = "Welcome to Bhasha Mitra"

    inputs = tokenizer(
        text,
        return_tensors="pt",
    )

    with torch.no_grad():

        generated = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids("mar_Deva"),
            max_new_tokens=128,
        )

    result = tokenizer.batch_decode(
        generated,
        skip_special_tokens=True,
    )[0]

    print("\nInput")
    print("-" * 80)
    print(text)

    print("\nOutput")
    print("-" * 80)
    print(result)

    banner("LOADED MODEL VALIDATION PASSED")

except Exception as exc:

    banner("LOADED MODEL VALIDATION FAILED")

    print(type(exc).__name__)
    print(exc)
    print()

    traceback.print_exc()