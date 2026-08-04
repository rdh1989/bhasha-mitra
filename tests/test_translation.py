"""
===============================================================================
Bhasha Mitra - Translation Framework Validation
-------------------------------------------------------------------------------
Purpose:
    Validate Translation Framework end-to-end.

Flow
----
1. Initialize ModelManager
2. Load MarianMT model
3. Translate English → Marathi
4. Print translated text

Author:
    Bhasha Mitra AI Team
===============================================================================
"""

from pathlib import Path
import sys
import traceback

# ---------------------------------------------------------------------------
# Add Project Root
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def banner(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


try:

    banner("BHASHA MITRA - TRANSLATION VALIDATION")

    # -----------------------------------------------------------------------
    # Import
    # -----------------------------------------------------------------------

    print("\n[1/5] Importing ModelManager...")

    from ai.model_manager.manager import ModelManager

    print("PASS")

    # -----------------------------------------------------------------------
    # Create Manager
    # -----------------------------------------------------------------------

    print("\n[2/5] Creating ModelManager...")

    manager = ModelManager()

    print("PASS")

    # -----------------------------------------------------------------------
    # Initialize
    # -----------------------------------------------------------------------

    print("\n[3/5] Initializing Framework...")

    manager.initialize()

    print("PASS")

    # -----------------------------------------------------------------------
    # Load Translation Model
    # -----------------------------------------------------------------------

    print("\n[4/5] Loading Translation Model...")

    translation = manager.load_model(
        category="translation",
        model="NLLB-600M",
    )

    print("PASS")

    model = translation["model"]
    tokenizer = translation["tokenizer"]

    print("\nModel Name:")
    print(model.config._name_or_path)

    print("\nTokenizer Class:")
    print(type(tokenizer).__name__)

    print("\nModel Class:")
    print(type(model).__name__)

    # -----------------------------------------------------------------------
    # Translation
    # -----------------------------------------------------------------------

    print("\n[5/5] Running Translation...")

    english_text = (
        "Welcome to Bhasha Mitra. "
        "This is an English to Marathi translation test."
    )

    print("\nInput")
    print("-" * 80)
    print(english_text)

    inputs = tokenizer(
        english_text,
        return_tensors="pt",
        padding=True,
    )

    translated = model.generate(**inputs)

    marathi = tokenizer.batch_decode(
        translated,
        skip_special_tokens=True,
    )[0]

    print("\nOutput")
    print("-" * 80)
    print(marathi)

    banner("TRANSLATION FRAMEWORK VALIDATION PASSED")

except Exception as exc:

    banner("TRANSLATION FRAMEWORK VALIDATION FAILED")

    print(type(exc).__name__)
    print(exc)

    print("\n")

    traceback.print_exc()