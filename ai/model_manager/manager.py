"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : manager.py
Purpose     : Central AI Model Manager

Description:
    Singleton responsible for AI model lifecycle management.

Design Pattern:
    Singleton

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""
from __future__ import annotations

import gc

from threading import Lock
from typing import Any
from pathlib import Path

from ai.model_manager.cache import ModelCache
from ai.model_manager.loader import ModelLoader
from ai.model_manager.manifest import ManifestReader
from ai.model_manager.registry import ModelRegistry
from ai.model_manager.validator import ModelValidator
from ai.model_manager.downloader import ModelDownloader


class ModelManager:
    """
    Singleton responsible for managing AI models.

    Responsibilities
    ----------------
    • Read model manifest
    • Validate model metadata
    • Register models
    • Load models
    • Cache loaded models
    • Unload models
    • Provide loaded models to providers

    Notes
    -----
    This is the only public entry point of the model_manager package.
    """

    _instance: "ModelManager | None" = None
    _lock = Lock()

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:

        if hasattr(self, "_initialized"):
            return

        self._initialized = True

        self._registry = ModelRegistry()
        self._validator = ModelValidator()
        self._loader = ModelLoader(self._registry)
        self._cache = ModelCache()
        self._manifest = ManifestReader()
        self._downloader = ModelDownloader()

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    # def initialize(self) -> None:
    #     """
    #     Initialize Model Manager.

    #     Responsibilities
    #     ----------------
    #     • Read manifest.json
    #     • Validate manifest
    #     • Validate model directories
    #     • Populate ModelRegistry
    #     """

    #     manifest_path = Path("config/manifest.json")

    #     # Read manifest
    #     manifest = self._manifest.read(manifest_path)

    #     # Validate manifest structure
    #     self._validator.validate_manifest(manifest)

    #     # Register every model
    #     for category, metadata in manifest.items():

    #         # Skip non-model sections
    #         if category == "ffmpeg":
    #             continue

    #         provider = metadata["provider"]
    #         print(f"Registering model: {category} - {provider}")
    #         model = metadata["model"]
    #         # model_path = Path(metadata["path"])
    #         # Resolve relative model path against project root
    #         project_root = Path(__file__).resolve().parents[2]
    #         model_path = project_root / metadata["path"]
    #         model_path = model_path.resolve()            
    #         version = metadata.get("version", "unknown")

    #         if metadata.get("requires_model_directory"):
    #             # Validate directory exists
    #             self._validator.validate_directory(model_path)

    #         # Register model
    #         self._registry.register(
    #             category=category,
    #             model=model,
    #             model_path=model_path,
    #             provider=provider,
    #             version=version,
    #         )

    def initialize(self) -> None:
        """
        Initialize Model Manager.

        Responsibilities
        ----------------
        • Read manifest.json
        • Validate manifest
        • Register available AI assets
        """

        manifest_path = Path("config/manifest.json")

        # Read manifest
        manifest = self._manifest.read(manifest_path)

        # Validate manifest structure
        self._validator.validate_manifest(manifest)

        # Project root
        project_root = Path(__file__).resolve().parents[2]

        for category, metadata in manifest.items():

            if category == "ffmpeg":
                continue

            provider = metadata["provider"]

            # ----------------------------------------------------------
            # Resolve asset name
            # ASR / Translation -> model
            # TTS -> voice
            # ----------------------------------------------------------
            asset_name = metadata.get("model") or metadata.get("voice")

            if asset_name is None:
                raise KeyError(
                    f"Manifest section '{category}' must define either "
                    "'model' or 'voice'."
                )

            print(f"Registering {category}: {asset_name}")

            version = metadata.get("version", "unknown")

            model_path = None

            if "path" in metadata:

                model_path = (
                    project_root / metadata["path"]
                ).resolve()

                if metadata.get("requires_model_directory"):
                    # Validate directory exists
                    self._validator.validate_directory(model_path)
                # Validate only if a filesystem asset exists
                # self._validator.validate_directory(model_path)

            self._registry.register(
                category=category,
                model=asset_name,
                model_path=model_path,
                provider=provider,
                version=version,
            )
    # -------------------------------------------------------------------------
    # Model Operations
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # Bulk Loading
    # -------------------------------------------------------------------------

    def load_all(self) -> None:
        """
        Load every registered model into memory.

        Called once during application startup.
        """

        print("\nLoading AI Models...\n")

        for key in self._registry.list():

            category, model = key.split(":", 1)

            print(f"Loading {category}:{model}")

            if category == "language_detection":
                print(
                    f"Skipping {category}:{model} "
                    "as it is not loaded at startup."
                )
                continue
            
            self.load_model(
                category=category,
                model=model,
            )
        print("\nAll AI Models Loaded.")


    def load_model(
        self,
        category: str,
        model: str,
    ) -> Any:
        """
        Load model into memory.

        Returns cached model if already loaded.
        """

        cache_key = f"{category}:{model}"

        if self._cache.exists(cache_key):
            return self._cache.get(cache_key)

        loaded_model = self._loader.load(category, model)

        self._cache.add(cache_key, loaded_model)

        return loaded_model    

        # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Default Model
    # -------------------------------------------------------------------------

    def get_default_model(
        self,
        category: str,
    ):
        """
        Return the default loaded model for a category.

        Parameters
        ----------
        category : str
            AI category (translation, asr, tts, ...)

        Returns
        -------
        Any
            Loaded model instance.

        Raises
        ------
        RuntimeError
            If no model is registered or loaded.
        """

        for key in self._registry.list():

            registered_category, model_name = key.split(":", 1)

            if registered_category != category:
                continue

            if not self.is_loaded(category, model_name):
                raise RuntimeError(
                    f"Model '{category}:{model_name}' is not loaded."
                )

            return self.get_model(
                category=category,
                model=model_name,
            )

        raise RuntimeError(
            f"No model registered for '{category}'."
        )


    def get_default_metadata(
        self,
        category: str,
    ) -> dict:
        """
        Return metadata for the default model of a category.
        """

        for key in self._registry.list():

            registered_category, model_name = key.split(":", 1)

            if registered_category == category:
                return self._registry.get(
                    category,
                    model_name,
                )

        raise RuntimeError(
            f"No model registered for '{category}'."
        )

    def get_model(
        self,
        category: str,
        model: str,
    ) -> Any:
        """
        Return loaded model.
        """
        return self._cache.get(f"{category}:{model}")

    def unload_model(self, category: str, model: str) -> None:
        """
        Remove model from memory.
        """

        cache_key = f"{category}:{model}"

        if not self._cache.exists(cache_key):
            return

        model = self._cache.get(cache_key)

        self._loader.unload(model)

        self._cache.remove(cache_key    )


    def unload(
        self,
        model: Any,
    ) -> None:

        #
        # Remove local reference
        #
        del model

        #
        # Force Python GC
        #
        gc.collect()

        #
        # Future GPU cleanup
        #
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception:
            pass
    # -------------------------------------------------------------------------
    # Query
    # -------------------------------------------------------------------------

    def is_loaded(
        self,
        category: str,
        model: str,
    ) -> bool:
        """
        Check whether model is loaded.
        """
        return self._cache.exists(f"{category}:{model}")

    def list_loaded_models(self) -> list[str]:
        """
        Return names of loaded models.
        """

        return self._cache.list()

    # -------------------------------------------------------------------------
    # Shutdown
    # -------------------------------------------------------------------------

    def shutdown(self) -> None:

        loaded = list(self._cache.list())

        for cache_key in loaded:

            category, model = cache_key.split(":", 1)

            print(f"Unloading {cache_key}")

            self.unload_model(category, model)

        #
        # Safety
        #
        self._cache.clear()

        # import gc

        gc.collect()

        print("All AI Models Unloaded.")

        print("All AI Models Unloaded.")