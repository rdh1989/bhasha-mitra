from ai.model_manager.manager import ModelManager


def test_shutdown_clears_cache_and_flushes_gc():
    manager = ModelManager()

    class FakeCache:
        def __init__(self):
            self.items = {}

        def exists(self, key):
            return key in self.items

        def get(self, key):
            return self.items[key]

        def add(self, key, value):
            self.items[key] = value

        def remove(self, key):
            self.items.pop(key, None)

        def clear(self):
            self.items.clear()

        def list(self):
            return list(self.items.keys())

    manager._cache = FakeCache()
    manager._cache.add("asr:demo", object())

    manager.shutdown()

    assert manager.list_loaded_models() == []
