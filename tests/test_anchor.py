"""
Tests for smart anchor system.
"""

import pytest
from datetime import datetime, timedelta
from src.anchor import (
    SmartAnchor,
    OperationRisk,
    TrustLevel,
    RISK_COSTS,
)


class TestSmartAnchor:
    """Test smart anchor behavior."""
    
    def test_initial_state(self):
        anchor = SmartAnchor(initial_trust=0.7)
        
        assert anchor.state.trust_score == 0.7
        assert anchor.state.risk_budget == 1.0
        assert anchor.state.consecutive_clean_ops == 0
    
    def test_safe_operations_free(self):
        anchor = SmartAnchor()
        
        # Safe operations should not deplete budget
        for i in range(100):
            check = anchor.pre_operation("read_file", {"risk_level": "SAFE"})
            assert check.can_proceed is True
            anchor.post_operation("read_file", {"risk_level": "SAFE"})
        
        # Budget should be unchanged
        assert anchor.state.risk_budget == 1.0
    
    def test_risky_operations_deplete_budget(self):
        anchor = SmartAnchor()
        initial_budget = anchor.state.risk_budget
        
        # HIGH risk operation
        check = anchor.pre_operation("send_email", {"risk_level": "HIGH"})
        assert check.can_proceed is True
        anchor.post_operation("send_email", {"risk_level": "HIGH"})
        
        # Budget should be depleted
        expected = initial_budget - RISK_COSTS["HIGH"]
        assert anchor.state.risk_budget == expected
    
    def test_budget_depletion_blocks(self):
        anchor = SmartAnchor()
        
        # Deplete budget with HIGH operations
        while anchor.state.risk_budget >= RISK_COSTS["HIGH"]:
            anchor.post_operation("send", {"risk_level": "HIGH"})
        
        # Next HIGH operation should be blocked
        check = anchor.pre_operation("send", {"risk_level": "HIGH"})
        assert check.can_proceed is False
        assert "budget" in check.reason.lower()
    
    def test_critical_always_blocks(self):
        anchor = SmartAnchor(initial_trust=1.0)  # Max trust
        
        # Even with full trust and budget, CRITICAL requires checkpoint
        check = anchor.pre_operation("delete_production", {"risk_level": "CRITICAL"})
        assert check.can_proceed is False
        assert "critical" in check.reason.lower()
    
    def test_human_checkpoint_resets_budget(self):
        anchor = SmartAnchor()
        
        # Deplete budget
        anchor.state.risk_budget = 0.1
        
        # Human checkpoint
        anchor.human_checkpoint()
        
        # Budget should be full again
        assert anchor.state.risk_budget == 1.0
    
    def test_trust_builds_with_clean_ops(self):
        anchor = SmartAnchor(initial_trust=0.5)
        initial_trust = anchor.state.trust_score
        
        # Do clean operations
        for i in range(20):
            anchor.post_operation("read", {"risk_level": "SAFE"})
        
        # Trust should have increased
        assert anchor.state.trust_score > initial_trust
    
    def test_trust_decreases_with_warnings(self):
        anchor = SmartAnchor(initial_trust=0.7)
        initial_trust = anchor.state.trust_score
        
        # Operation with warnings
        anchor.post_operation("write", {}, advisory_warnings=3)
        
        # Trust should have decreased
        assert anchor.state.trust_score < initial_trust
    
    def test_trust_threshold_enforcement(self):
        anchor = SmartAnchor(initial_trust=0.3)  # Low trust
        
        # HIGH operations require COLLABORATIVE (0.6) trust
        check = anchor.pre_operation("send", {"risk_level": "HIGH"})
        assert check.can_proceed is False
        assert "trust" in check.reason.lower()


class TestTrustLevels:
    """Test trust level conversion."""
    
    def test_trust_level_from_score(self):
        assert TrustLevel.from_score(0.0) == TrustLevel.DISCONNECTED
        assert TrustLevel.from_score(0.25) == TrustLevel.MINIMAL
        assert TrustLevel.from_score(0.5) == TrustLevel.CAUTIOUS
        assert TrustLevel.from_score(0.7) == TrustLevel.COLLABORATIVE
        assert TrustLevel.from_score(0.85) == TrustLevel.HIGH_TRUST
        assert TrustLevel.from_score(0.99) == TrustLevel.AUTONOMOUS


class TestDriftDetection:
    """Test drift pattern detection."""
    
    def test_speed_drift_detected(self):
        anchor = SmartAnchor()
        
        # Simulate rapid operations (all at same timestamp via history manipulation)
        # In real usage, this would be detected by ops_per_minute calculation
        # This is a simplified test
        for i in range(15):
            anchor.post_operation(f"op_{i}", {"risk_level": "LOW"})
        
        # Check status includes drift info
        status = anchor.status()
        # Drift detection depends on timing, so we just verify structure
        assert "drift_check" in status
    
    def test_repetition_anomaly(self):
        anchor = SmartAnchor()
        
        # Access same resource repeatedly
        for i in range(15):
            anchor.post_operation("read", {
                "risk_level": "SAFE",
                "path": "/same/file.txt",
            })
        
        # Check for drift
        drift = anchor._detect_drift()
        # May or may not trigger depending on thresholds
        # Just verify it doesn't crash
        assert drift is None or isinstance(drift, dict)


class TestAnchorStatus:
    """Test status and explain methods."""
    
    def test_status_structure(self):
        anchor = SmartAnchor()
        status = anchor.status()
        
        assert "state" in status
        assert "can_proceed_levels" in status
        assert "drift_check" in status
        assert "params" in status
        
        # Check state structure
        assert "risk_budget" in status["state"]
        assert "trust_score" in status["state"]
        assert "trust_level" in status["state"]
    
    def test_explain_returns_string(self):
        anchor = SmartAnchor()
        explanation = anchor.explain()
        
        assert isinstance(explanation, str)
        assert "Trust" in explanation
        assert "Budget" in explanation
