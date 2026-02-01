#!/usr/bin/env python3
"""
Equilibrium Guard — Lightweight Self-Monitoring Guard
======================================================

Single-file guard for OpenClaw skill integration.
Tracks trust, budget, and provides pre/post operation checks.

Usage:
    from guard import EQGuard
    
    guard = EQGuard()
    
    # Before operation
    can, reason = guard.check("web_fetch", risk="HIGH")
    if not can:
        print(f"Blocked: {reason}")
    
    # After operation
    guard.record("web_fetch", risk="HIGH")
    
    # Human interaction
    guard.checkpoint()
    
    # Status
    print(guard.status())
"""

import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass, field


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = {
    "initial_trust": 0.7,
    "budget_size": 1.0,
    "mode": "shadow",
    "risk_costs": {
        "SAFE": 0,
        "LOW": 0.05,
        "MEDIUM": 0.15,
        "HIGH": 0.40,
        "CRITICAL": 1.0,
    },
    "trust_required": {
        "SAFE": 0,
        "LOW": 0.2,
        "MEDIUM": 0.4,
        "HIGH": 0.6,
        "CRITICAL": 0.8,
    },
    "trust_boost_clean": 0.005,
    "trust_boost_streak": 0.01,
    "trust_boost_interaction": 0.05,
    "trust_boost_checkpoint": 0.1,
    "trust_penalty_warning": 0.02,
    "trust_penalty_violation": 0.2,
    "max_minutes_without_human": 60,
}


def load_config(config_path: Optional[Path] = None) -> Dict:
    """Load configuration from yaml file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    
    config = DEFAULT_CONFIG.copy()
    
    if config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            if file_config and "equilibrium_guard" in file_config:
                config.update(file_config["equilibrium_guard"])
    
    return config


# =============================================================================
# GUARD STATE
# =============================================================================

@dataclass
class GuardState:
    """Current guard state."""
    trust: float = 0.7
    budget: float = 1.0
    mode: str = "shadow"
    ops_since_checkpoint: int = 0
    clean_streak: int = 0
    last_human: datetime = field(default_factory=datetime.now)
    history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "trust": round(self.trust, 3),
            "budget": round(self.budget, 3),
            "mode": self.mode,
            "ops_since_checkpoint": self.ops_since_checkpoint,
            "clean_streak": self.clean_streak,
            "minutes_since_human": round(
                (datetime.now() - self.last_human).total_seconds() / 60, 1
            ),
        }


# =============================================================================
# EQUILIBRIUM GUARD
# =============================================================================

class EQGuard:
    """
    Lightweight Equilibrium Guard for self-monitoring.
    
    Usage:
        guard = EQGuard()
        
        can, reason = guard.check("operation_name", risk="MEDIUM")
        if can:
            do_operation()
            guard.record("operation_name", risk="MEDIUM")
        else:
            ask_human(reason)
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.state = GuardState(
            trust=self.config["initial_trust"],
            budget=self.config["budget_size"],
            mode=self.config.get("mode", "shadow"),
        )
        self._dashboard_url = self.config.get("dashboard_url", "http://localhost:8081")
    
    # =========================================================================
    # CORE API
    # =========================================================================
    
    def check(self, operation: str, risk: str = "SAFE", context: Dict = None) -> Tuple[bool, str]:
        """
        Check if operation can proceed.
        
        Returns (can_proceed, reason).
        """
        context = context or {}
        risk = risk.upper()
        
        # Mode: disabled
        if self.state.mode == "disabled":
            return True, "Guard disabled"
        
        # CRITICAL always needs checkpoint
        if risk == "CRITICAL":
            return False, "CRITICAL operations require human confirmation"
        
        # Check trust threshold
        required_trust = self.config["trust_required"].get(risk, 0)
        if self.state.trust < required_trust:
            return False, f"Trust ({self.state.trust:.2f}) below required ({required_trust}) for {risk} operations"
        
        # Check budget
        cost = self.config["risk_costs"].get(risk, 0)
        if self.state.budget < cost:
            return False, f"Budget depleted ({self.state.budget:.2f}). Need {cost} for {risk} operation."
        
        # Check time since human
        minutes = (datetime.now() - self.state.last_human).total_seconds() / 60
        max_minutes = self.config.get("max_minutes_without_human", 60)
        if minutes > max_minutes and risk in ["MEDIUM", "HIGH"]:
            return False, f"No human interaction for {minutes:.0f} minutes. Checkpoint for {risk} operations."
        
        # Shadow/soft mode adjustments
        if self.state.mode == "shadow":
            return True, "Shadow mode (would check in enforce mode)"
        
        if self.state.mode == "soft" and risk not in ["HIGH", "CRITICAL"]:
            return True, "Soft mode (only blocks HIGH/CRITICAL)"
        
        return True, "Proceed"
    
    def record(self, operation: str, risk: str = "SAFE", warning: bool = False, violation: bool = False):
        """Record completed operation and adjust state."""
        risk = risk.upper()
        
        # Deduct budget
        cost = self.config["risk_costs"].get(risk, 0)
        self.state.budget = max(0, self.state.budget - cost)
        self.state.ops_since_checkpoint += 1
        
        # Adjust trust
        if violation:
            self.state.trust = max(0, self.state.trust - self.config["trust_penalty_violation"])
            self.state.clean_streak = 0
        elif warning:
            self.state.trust = max(0, self.state.trust - self.config["trust_penalty_warning"])
            self.state.clean_streak = 0
        else:
            self.state.trust = min(1.0, self.state.trust + self.config["trust_boost_clean"])
            self.state.clean_streak += 1
            if self.state.clean_streak >= 10:
                self.state.trust = min(1.0, self.state.trust + self.config["trust_boost_streak"])
        
        # Record in history
        self.state.history.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "risk": risk,
            "budget_after": self.state.budget,
            "trust_after": self.state.trust,
        })
        
        # Trim history
        if len(self.state.history) > 100:
            self.state.history = self.state.history[-100:]
        
        # Send to dashboard if available
        self._send_to_dashboard(operation, risk, warning, violation)
    
    def checkpoint(self):
        """Human checkpoint — reset budget, boost trust."""
        self.state.budget = self.config["budget_size"]
        self.state.trust = min(1.0, self.state.trust + self.config["trust_boost_checkpoint"])
        self.state.last_human = datetime.now()
        self.state.ops_since_checkpoint = 0
        self.state.clean_streak = 0
    
    def human_message(self):
        """Human sent a message — update last interaction."""
        self.state.last_human = datetime.now()
        self.state.trust = min(1.0, self.state.trust + self.config["trust_boost_interaction"])
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def status(self) -> str:
        """Get human-readable status."""
        s = self.state
        trust_level = self._trust_level(s.trust)
        
        lines = [
            f"Trust: {s.trust:.2f} ({trust_level})",
            f"Budget: {s.budget:.2f} / {self.config['budget_size']}",
            f"Mode: {s.mode.upper()}",
            f"Ops since checkpoint: {s.ops_since_checkpoint}",
            f"Clean streak: {s.clean_streak}",
        ]
        
        if s.budget < 0.3:
            lines.append("⚠️ Low budget — checkpoint recommended")
        
        return "\n".join(lines)
    
    def status_dict(self) -> Dict:
        """Get status as dictionary."""
        return self.state.to_dict()
    
    def can_do(self, risk: str) -> bool:
        """Quick check: can we do this risk level?"""
        can, _ = self.check("check", risk=risk)
        return can
    
    # =========================================================================
    # MODE
    # =========================================================================
    
    def set_mode(self, mode: str):
        """Set guard mode: disabled | shadow | soft | enforce."""
        if mode in ["disabled", "shadow", "soft", "enforce"]:
            self.state.mode = mode
    
    # =========================================================================
    # INTERNAL
    # =========================================================================
    
    def _trust_level(self, trust: float) -> str:
        """Convert trust score to level name."""
        if trust >= 0.95:
            return "AUTONOMOUS"
        elif trust >= 0.8:
            return "HIGH_TRUST"
        elif trust >= 0.6:
            return "COLLABORATIVE"
        elif trust >= 0.4:
            return "CAUTIOUS"
        elif trust >= 0.2:
            return "MINIMAL"
        else:
            return "DISCONNECTED"
    
    def _send_to_dashboard(self, operation: str, risk: str, warning: bool, violation: bool):
        """Send decision to dashboard (fire and forget)."""
        try:
            import requests
            requests.post(
                f"{self._dashboard_url}/api/decision",
                json={
                    "timestamp": datetime.now().isoformat(),
                    "operation": operation,
                    "risk_level": risk,
                    "would_block": False,
                    "actually_blocked": False,
                    "reasons": [],
                    "trust_score": self.state.trust,
                    "budget_remaining": self.state.budget,
                },
                timeout=0.5,
            )
        except Exception:
            pass  # Dashboard not available, ignore


# =============================================================================
# CONVENIENCE
# =============================================================================

# Global instance
_guard: Optional[EQGuard] = None


def get_guard() -> EQGuard:
    """Get or create global guard instance."""
    global _guard
    if _guard is None:
        _guard = EQGuard()
    return _guard


def check(operation: str, risk: str = "SAFE") -> Tuple[bool, str]:
    """Check operation using global guard."""
    return get_guard().check(operation, risk)


def record(operation: str, risk: str = "SAFE", warning: bool = False):
    """Record operation using global guard."""
    get_guard().record(operation, risk, warning)


def checkpoint():
    """Human checkpoint using global guard."""
    get_guard().checkpoint()


def status() -> str:
    """Get status from global guard."""
    return get_guard().status()


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    guard = EQGuard()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "status":
            print(guard.status())
        
        elif cmd == "check" and len(sys.argv) > 2:
            risk = sys.argv[2].upper()
            can, reason = guard.check("cli_check", risk=risk)
            print(f"Can proceed: {can}")
            print(f"Reason: {reason}")
        
        elif cmd == "checkpoint":
            guard.checkpoint()
            print("Checkpoint completed")
            print(guard.status())
        
        else:
            print("Usage: guard.py [status|check RISK|checkpoint]")
    else:
        print(guard.status())
