"""
Comprehensive unit tests for memory policy and OOM protection.

These tests ensure the memory policy correctly enforces 70% limits,
handles model loading with memory constraints, and prevents OOM.
"""
import unittest
from unittest.mock import patch, MagicMock
import os

from app.models.memory_policy import (
    MemoryPolicy, MemoryState, MemoryBudgetExceeded, get_memory_policy
)


class TestMemoryPolicyCalculations(unittest.TestCase):
    """Test memory limit calculations."""
    
    def setUp(self):
        """Clear any global state before each test."""
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_default_70_percent_limit(self):
        """Test default 70% memory limit is correctly calculated."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)  # 24 GB
                
                policy = MemoryPolicy()
                
                self.assertEqual(policy.limit_percent, 70)
                self.assertAlmostEqual(policy.physical_memory_gb, 24.0, places=1)
                # 70% of 24 GB = 16.8 GB
                self.assertAlmostEqual(policy.configured_limit_gb, 16.8, places=1)
    
    def test_configurable_memory_limit_percent(self):
        """Test memory limit percentage is configurable."""
        with patch.dict(os.environ, {"MEMORY_USAGE_LIMIT_PERCENT": "80"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                policy = MemoryPolicy()
                
                self.assertEqual(policy.limit_percent, 80)
                # 80% of 24 GB = 19.2 GB
                self.assertAlmostEqual(policy.configured_limit_gb, 19.2, places=1)
    
    def test_safety_margin_reduces_hard_limit(self):
        """Test safety margin is subtracted from configured limit."""
        with patch.dict(os.environ, {"MEMORY_SAFETY_MARGIN_GB": "1.0"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                policy = MemoryPolicy()
                
                self.assertEqual(policy.safety_margin_gb, 1.0)
                # hard_limit = (24 * 0.70) - 1.0 = 16.8 - 1.0 = 15.8 GB
                self.assertAlmostEqual(policy.hard_limit_gb, 15.8, places=1)
    
    def test_warning_threshold_percent(self):
        """Test warning threshold is correctly calculated."""
        with patch.dict(os.environ, {"MEMORY_WARNING_THRESHOLD_PERCENT": "50"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                policy = MemoryPolicy()
                
                # 50% of configured_limit (16.8 GB) = 8.4 GB
                self.assertAlmostEqual(policy.warning_limit_gb, 8.4, places=1)
    
    def test_memory_percent_clamped_to_valid_range(self):
        """Test memory percent is clamped to 10-90% range."""
        # Test too low
        with patch.dict(os.environ, {"MEMORY_USAGE_LIMIT_PERCENT": "5"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                policy = MemoryPolicy()
                self.assertEqual(policy.limit_percent, 10)  # Clamped to minimum
        
        # Test too high
        with patch.dict(os.environ, {"MEMORY_USAGE_LIMIT_PERCENT": "95"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                policy = MemoryPolicy()
                self.assertEqual(policy.limit_percent, 90)  # Clamped to maximum


class TestMemoryStateDetection(unittest.TestCase):
    """Test memory state detection logic."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_memory_ok_state(self):
        """Test MEMORY_OK state when under limit."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Process using 10 GB, limit is 16.8 GB
                    mock_proc.return_value.memory_info.return_value.rss = 10 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    state = policy.get_memory_state()
                    
                    self.assertEqual(state, MemoryState.MEMORY_OK)
    
    def test_memory_warning_state(self):
        """Test MEMORY_WARNING state when approaching limit."""
        with patch.dict(os.environ, {"MEMORY_WARNING_THRESHOLD_PERCENT": "60"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # configured_limit = 16.8 GB, warning = 60% of 16.8 = 10.08 GB
                    # Process at 11 GB (exceeds warning but under hard limit)
                    mock_proc.return_value.memory_info.return_value.rss = 11 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    state = policy.get_memory_state()
                    
                    self.assertEqual(state, MemoryState.MEMORY_WARNING)
    
    def test_memory_limit_exceeded_state(self):
        """Test MEMORY_LIMIT_EXCEEDED state when over hard limit."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # hard_limit = 16.3 GB (70% of 24 - 0.5 safety)
                    # Process at 17 GB (exceeds hard limit)
                    mock_proc.return_value.memory_info.return_value.rss = 17 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    state = policy.get_memory_state()
                    
                    self.assertEqual(state, MemoryState.MEMORY_LIMIT_EXCEEDED)
    
    def test_policy_disabled_always_ok(self):
        """Test disabled policy always returns MEMORY_OK."""
        with patch.dict(os.environ, {"MEMORY_POLICY_ENABLED": "false"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Even at 99 GB (way over limit)
                    mock_proc.return_value.memory_info.return_value.rss = 99 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    state = policy.get_memory_state()
                    
                    self.assertEqual(state, MemoryState.MEMORY_OK)


class TestModelLoadAdmissionControl(unittest.TestCase):
    """Test model loading admission control."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_model_fits_in_budget(self):
        """Test model loading allowed when sufficient memory exists."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Process at 8 GB, model 1B at ~6.5 GB estimated
                    # Peak estimated = 8 + (6.5 * 1.5) = 17.75 GB, hard limit 16.3 GB
                    # This should fit
                    mock_proc.return_value.memory_info.return_value.rss = 6 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    can_load, reason, diags = policy.can_load_model("IndicTrans2-1B", 6.5)
                    
                    self.assertTrue(can_load)
                    self.assertEqual(diags["model_id"], "IndicTrans2-1B")
    
    def test_model_does_not_fit_raises_exception(self):
        """Test model loading rejected when would exceed budget."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Process already at 12 GB
                    # Model 1B at ~6.5 GB would peak at 12 + (6.5 * 1.5) = 21.75 GB
                    # hard limit is 16.3 GB, so should fail
                    mock_proc.return_value.memory_info.return_value.rss = 12 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    
                    with self.assertRaises(MemoryBudgetExceeded) as ctx:
                        policy.can_load_model("IndicTrans2-1B", 6.5)
                    
                    exc = ctx.exception
                    self.assertEqual(exc.model_id, "IndicTrans2-1B")
                    self.assertIn("peak memory", exc.message.lower())
    
    def test_already_over_limit_rejects_any_load(self):
        """Test loading rejected if already over hard limit."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Process already at 17 GB, hard limit 16.3 GB
                    mock_proc.return_value.memory_info.return_value.rss = 17 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    
                    with self.assertRaises(MemoryBudgetExceeded):
                        policy.can_load_model("ASR-model", 1.0)
    
    def test_disabled_policy_allows_any_load(self):
        """Test disabled policy allows loading regardless of memory."""
        with patch.dict(os.environ, {"MEMORY_POLICY_ENABLED": "false"}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Process at 99 GB
                    mock_proc.return_value.memory_info.return_value.rss = 99 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    can_load, reason, diags = policy.can_load_model("model", 1.0)
                    
                    self.assertTrue(can_load)
                    self.assertIn("disabled", reason.lower())


class TestMemoryDiagnostics(unittest.TestCase):
    """Test memory diagnostics and logging."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_load_metrics_logging(self):
        """Test that load metrics are correctly reported."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    mock_proc.return_value.memory_info.return_value.rss = 10 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    
                    # Should not raise
                    policy.log_load_metrics("test-model", 10.0, 11.5, 5.2)
    
    def test_memory_during_job_checkpoint(self):
        """Test memory checking during job checkpoints."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    mock_proc.return_value.memory_info.return_value.rss = 10 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    ok = policy.check_memory_during_job("job-123", "translation_1")
                    
                    self.assertTrue(ok)


class TestProcessMemoryMeasurement(unittest.TestCase):
    """Test process memory measurement."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_process_memory_gb_conversion(self):
        """Test process memory is correctly converted to GB."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # 2 GB in bytes
                    mock_proc.return_value.memory_info.return_value.rss = 2 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    memory_gb = policy.get_process_memory_gb()
                    
                    self.assertAlmostEqual(memory_gb, 2.0, places=2)
    
    def test_process_memory_fallback(self):
        """Test graceful fallback when memory query fails."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    mock_proc.side_effect = Exception("psutil error")
                    
                    policy = MemoryPolicy()
                    memory_gb = policy.get_process_memory_gb()
                    
                    # Should return 0.0 on error
                    self.assertEqual(memory_gb, 0.0)


class TestGlobalPolicyInstance(unittest.TestCase):
    """Test global memory policy singleton."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_get_memory_policy_returns_singleton(self):
        """Test get_memory_policy returns the same instance."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                policy1 = get_memory_policy()
                policy2 = get_memory_policy()
                
                self.assertIs(policy1, policy2)


class TestTranslationJobMemorySafety(unittest.TestCase):
    """Integration tests for translation job OOM protection."""
    
    def setUp(self):
        import app.models.memory_policy as mp_module
        mp_module._memory_policy = None
    
    def test_translation_1b_model_fits_24gb_machine(self):
        """Test 1B translation model fits within 70% of 24 GB."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # Application baseline ~3 GB
                    mock_proc.return_value.memory_info.return_value.rss = 3 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    
                    # Try to load 1B model (estimated 6.5 GB peak)
                    # Peak would be ~3 + (6.5 * 1.5) = 12.75 GB
                    # hard_limit = 16.3 GB
                    # Should fit
                    can_load, _, _ = policy.can_load_model("IndicTrans2-1B", 6.5)
                    self.assertTrue(can_load)
    
    def test_multiple_models_accumulation(self):
        """Test multiple models don't accumulate over limit."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value.total = 24 * (1024 ** 3)
                
                with patch("psutil.Process") as mock_proc:
                    # After loading translation (6.5 GB), ASR (1.5 GB), TTS (3.5 GB)
                    # Total ~11.5 GB, plus baseline 3 GB = 14.5 GB
                    mock_proc.return_value.memory_info.return_value.rss = 14.5 * (1024 ** 3)
                    
                    policy = MemoryPolicy()
                    
                    # Try to load one more model that would push over limit
                    # Peak = 14.5 + (3 * 1.5) = 18.5 GB, exceeds 16.3 GB
                    with self.assertRaises(MemoryBudgetExceeded):
                        policy.can_load_model("Parler-TTS", 3.0)


if __name__ == "__main__":
    unittest.main()
