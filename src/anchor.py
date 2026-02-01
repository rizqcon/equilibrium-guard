"""
Equilibrium Guard - Smart Anchor System
=========================================

Risk-weighted autonomy with continuous self-validation.

Core insight: "The human is not a user. The human is the ⚓️"

Key improvements over simple chain counting:
- Risk-weighted budget (safe ops are free, risky ops cost more)
- Dynamic trust score that builds/depletes based on behavior
- Pattern detection for drift analysis
- Continuous self-validation after each operation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import deque
import json


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class TrustLevel(Enum):
    """Trust level thresholds (mapped to 0.0 - 1.0 score)."""
    DISCONNECTED = 0.0    # No human oversight available
    MINIMAL = 0.2         # Human barely following
    CAUTIOUS = 0.4        # Human following but skeptical
    COLLABORATIVE = 0.6   # Normal working relationship
    HIGH_TRUST = 0.8      # Deep understanding
    AUTONOMOUS = 0.95     # Full delegation (rare)
    
    @classmethod
    def from_score(cls, score: float) -> 'TrustLevel':
        """Convert numeric score to trust level."""
        for level in reversed(list(cls)):
            if score >= level.value:
                return level
        return cls.DISCONNECTED


class OperationRisk(Enum):
    """Risk level of operations."""
    SAFE = "SAFE"           # Read-only, internal, reversible
    LOW = "LOW"             # Minor changes, easily reversible
    MEDIUM = "MEDIUM"       # Significant changes, reversible with effort
    HIGH = "HIGH"           # External actions, hard to reverse
    CRITICAL = "CRITICAL"   # Irreversible, public, or security-sensitive


# Risk costs - how much budget each risk level consumes
RISK_COSTS: Dict[str, float] = {
    "SAFE": 0.0,        # Unlimited
    "LOW": 0.05,        # ~20 ops before checkpoint
    "MEDIUM": 0.15,     # ~6-7 ops before checkpoint
    "HIGH": 0.4,        # 2-3 ops before checkpoint
    "CRITICAL": 1.0,    # Immediate checkpoint
}

# Minimum trust required for each risk level
RISK_TRUST_THRESHOLDS: Dict[str, float] = {
    "SAFE": 0.0,        # Always allowed
    "LOW": 0.2,         # MINIMAL trust
    "MEDIUM": 0.4,      # CAUTIOUS trust
    "HIGH": 0.6,        # COLLABORATIVE trust
    "CRITICAL": 0.8,    # HIGH_TRUST required
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class OperationRecord:
    """Record of a single operation for history tracking."""
    operation: str
    risk: str
    timestamp: datetime
    context_hash: str  # Summarized context for pattern detection
    resource: Optional[str] = None  # Primary resource accessed
    external: bool = False  # Was this an external operation?
    warnings: int = 0  # Advisory warnings triggered
    
    def to_dict(self) -> Dict:
        return {
            "operation": self.operation,
            "risk": self.risk,
            "timestamp": self.timestamp.isoformat(),
            "context_hash": self.context_hash,
            "resource": self.resource,
            "external": self.external,
            "warnings": self.warnings,
        }


@dataclass
class AnchorState:
    """Current state of the anchor system."""
    risk_budget: float = 1.0
    trust_score: float = 0.7  # Start at COLLABORATIVE
    last_checkpoint: datetime = field(default_factory=datetime.now)
    last_human_interaction: datetime = field(default_factory=datetime.now)
    consecutive_clean_ops: int = 0
    total_ops_since_checkpoint: int = 0
    warnings_since_checkpoint: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "risk_budget": round(self.risk_budget, 3),
            "trust_score": round(self.trust_score, 3),
            "trust_level": TrustLevel.from_score(self.trust_score).name,
            "last_checkpoint_minutes_ago": round(
                (datetime.now() - self.last_checkpoint).total_seconds() / 60, 1
            ),
            "last_human_interaction_minutes_ago": round(
                (datetime.now() - self.last_human_interaction).total_seconds() / 60, 1
            ),
            "consecutive_clean_ops": self.consecutive_clean_ops,
            "total_ops_since_checkpoint": self.total_ops_since_checkpoint,
            "warnings_since_checkpoint": self.warnings_since_checkpoint,
        }


@dataclass
class PreCheckResult:
    """Result of pre-operation check."""
    can_proceed: bool
    reason: str
    risk_level: str
    budget_after: float
    trust_level: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class PostCheckResult:
    """Result of post-operation validation."""
    valid: bool
    trust_delta: float
    budget_remaining: float
    drift_detected: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# DRIFT PATTERNS
# =============================================================================

class DriftDetector:
    """Analyzes operation history for concerning patterns."""
    
    @staticmethod
    def escalating_access(history: List[OperationRecord], window: int = 10) -> bool:
        """Detect if access levels are gradually increasing."""
        if len(history) < window:
            return False
        
        recent = history[-window:]
        risk_values = {"SAFE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        
        # Calculate trend
        first_half = sum(risk_values.get(op.risk, 0) for op in recent[:window//2])
        second_half = sum(risk_values.get(op.risk, 0) for op in recent[window//2:])
        
        # Significant increase in risk level
        return second_half > first_half * 1.5
    
    @staticmethod
    def external_drift(history: List[OperationRecord], window: int = 20) -> bool:
        """Detect increasing external operation frequency."""
        if len(history) < window:
            return False
        
        recent = history[-window:]
        first_half = sum(1 for op in recent[:window//2] if op.external)
        second_half = sum(1 for op in recent[window//2:] if op.external)
        
        # More than double external ops in second half
        return second_half > max(first_half * 2, 3)
    
    @staticmethod
    def speed_drift(history: List[OperationRecord], threshold_per_minute: int = 60) -> bool:
        """Detect if operations are happening faster than reasonable."""
        if len(history) < 10:
            return False
        
        recent = history[-10:]
        time_span = (recent[-1].timestamp - recent[0].timestamp).total_seconds()
        
        if time_span <= 0:
            return True  # All ops in same second = suspicious
        
        ops_per_minute = (len(recent) / time_span) * 60
        return ops_per_minute > threshold_per_minute
    
    @staticmethod
    def repetition_anomaly(history: List[OperationRecord], threshold: int = 10) -> bool:
        """Detect same resource being accessed repeatedly."""
        if len(history) < threshold:
            return False
        
        recent = history[-threshold:]
        resources = [op.resource for op in recent if op.resource]
        
        if not resources:
            return False
        
        # Check if any resource appears in >70% of recent ops
        from collections import Counter
        counts = Counter(resources)
        most_common_count = counts.most_common(1)[0][1]
        
        return most_common_count >= threshold * 0.7
    
    @staticmethod
    def warning_accumulation(history: List[OperationRecord], window: int = 10, threshold: int = 5) -> bool:
        """Detect if warnings are accumulating."""
        if len(history) < window:
            return False
        
        recent = history[-window:]
        total_warnings = sum(op.warnings for op in recent)
        
        return total_warnings >= threshold


DRIFT_PATTERNS = [
    {
        "name": "escalating_access",
        "description": "Risk levels gradually increasing",
        "detect": DriftDetector.escalating_access,
        "severity": "checkpoint",
    },
    {
        "name": "external_drift",
        "description": "External operations increasing",
        "detect": DriftDetector.external_drift,
        "severity": "reduce_budget",
    },
    {
        "name": "speed_drift",
        "description": "Operating faster than human can track",
        "detect": DriftDetector.speed_drift,
        "severity": "slow_down",
    },
    {
        "name": "repetition_anomaly",
        "description": "Same resource accessed repeatedly",
        "detect": DriftDetector.repetition_anomaly,
        "severity": "checkpoint",
    },
    {
        "name": "warning_accumulation",
        "description": "Too many advisory warnings",
        "detect": DriftDetector.warning_accumulation,
        "severity": "checkpoint",
    },
]


# =============================================================================
# SMART ANCHOR
# =============================================================================

class SmartAnchor:
    """
    Risk-weighted autonomy with continuous self-validation.
    
    Usage:
        anchor = SmartAnchor()
        
        # Before operation
        check = anchor.pre_operation("file_write", context)
        if not check.can_proceed:
            ask_human(check.reason)
            return
        
        # Execute operation
        result = do_operation()
        
        # After operation
        post = anchor.post_operation("file_write", context, advisory_warnings=0)
        if post.drift_detected:
            alert_human(post.drift_detected)
    """
    
    def __init__(
        self,
        initial_trust: float = 0.7,
        budget_size: float = 1.0,
        history_size: int = 100,
    ):
        self.state = AnchorState(
            risk_budget=budget_size,
            trust_score=initial_trust,
        )
        self.budget_size = budget_size
        self.history: deque[OperationRecord] = deque(maxlen=history_size)
        self.violation_callbacks: List[Callable[[str, Dict], None]] = []
        
        # Tunable parameters
        self.params = AnchorParams()
    
    # =========================================================================
    # CORE API
    # =========================================================================
    
    def pre_operation(
        self,
        operation: str,
        context: Dict[str, Any],
    ) -> PreCheckResult:
        """
        Check if operation can proceed.
        
        Call this BEFORE executing any operation.
        """
        risk = self._assess_risk(operation, context)
        cost = RISK_COSTS[risk]
        min_trust = RISK_TRUST_THRESHOLDS[risk]
        warnings = []
        
        # CRITICAL always requires checkpoint
        if risk == "CRITICAL":
            return PreCheckResult(
                can_proceed=False,
                reason="Critical operation requires human confirmation",
                risk_level=risk,
                budget_after=self.state.risk_budget,
                trust_level=TrustLevel.from_score(self.state.trust_score).name,
            )
        
        # Check trust threshold
        if self.state.trust_score < min_trust:
            return PreCheckResult(
                can_proceed=False,
                reason=f"Trust ({self.state.trust_score:.2f}) below threshold ({min_trust}) for {risk} operations",
                risk_level=risk,
                budget_after=self.state.risk_budget,
                trust_level=TrustLevel.from_score(self.state.trust_score).name,
            )
        
        # Check budget
        budget_after = self.state.risk_budget - cost
        if budget_after < 0:
            return PreCheckResult(
                can_proceed=False,
                reason=f"Risk budget depleted ({self.state.risk_budget:.2f} remaining, need {cost}). Checkpoint required.",
                risk_level=risk,
                budget_after=self.state.risk_budget,
                trust_level=TrustLevel.from_score(self.state.trust_score).name,
            )
        
        # Check for drift patterns
        drift = self._detect_drift()
        if drift and drift["severity"] == "checkpoint":
            return PreCheckResult(
                can_proceed=False,
                reason=f"Drift pattern detected: {drift['name']} — {drift['description']}",
                risk_level=risk,
                budget_after=self.state.risk_budget,
                trust_level=TrustLevel.from_score(self.state.trust_score).name,
            )
        elif drift:
            warnings.append(f"Drift warning: {drift['name']}")
        
        # Check time since last human interaction
        time_since_human = datetime.now() - self.state.last_human_interaction
        if time_since_human > timedelta(minutes=self.params.max_minutes_without_human):
            if risk in ["MEDIUM", "HIGH"]:
                return PreCheckResult(
                    can_proceed=False,
                    reason=f"No human interaction for {time_since_human.total_seconds()/60:.0f} minutes. Checkpoint for {risk} operations.",
                    risk_level=risk,
                    budget_after=self.state.risk_budget,
                    trust_level=TrustLevel.from_score(self.state.trust_score).name,
                )
        
        # All checks passed
        return PreCheckResult(
            can_proceed=True,
            reason="Proceed",
            risk_level=risk,
            budget_after=budget_after,
            trust_level=TrustLevel.from_score(self.state.trust_score).name,
            warnings=warnings,
        )
    
    def post_operation(
        self,
        operation: str,
        context: Dict[str, Any],
        advisory_warnings: int = 0,
        constraint_violation: bool = False,
    ) -> PostCheckResult:
        """
        Validate and record operation after execution.
        
        Call this AFTER each operation completes.
        """
        risk = self._assess_risk(operation, context)
        cost = RISK_COSTS[risk]
        recommendations = []
        
        # Deduct from budget
        self.state.risk_budget = max(0, self.state.risk_budget - cost)
        self.state.total_ops_since_checkpoint += 1
        
        # Record in history
        record = OperationRecord(
            operation=operation,
            risk=risk,
            timestamp=datetime.now(),
            context_hash=self._hash_context(context),
            resource=context.get("path") or context.get("resource") or context.get("url"),
            external=context.get("is_external", False),
            warnings=advisory_warnings,
        )
        self.history.append(record)
        
        # Adjust trust based on outcome
        trust_delta = 0.0
        
        if constraint_violation:
            # Violation: significant trust penalty
            trust_delta = -self.params.trust_penalty_violation
            self.state.consecutive_clean_ops = 0
            recommendations.append("Constraint violation detected — recommend checkpoint")
        elif advisory_warnings > 0:
            # Warnings: small penalty
            trust_delta = -self.params.trust_penalty_warning * advisory_warnings
            self.state.warnings_since_checkpoint += advisory_warnings
            self.state.consecutive_clean_ops = 0
        else:
            # Clean operation: tiny boost
            trust_delta = self.params.trust_boost_clean
            self.state.consecutive_clean_ops += 1
            
            # Bonus for sustained clean operations
            if self.state.consecutive_clean_ops >= 10:
                trust_delta += self.params.trust_boost_streak
        
        self.state.trust_score = max(0.0, min(1.0, self.state.trust_score + trust_delta))
        
        # Check for drift
        drift = self._detect_drift()
        drift_name = None
        
        if drift:
            drift_name = drift["name"]
            if drift["severity"] == "reduce_budget":
                self.state.risk_budget = max(0, self.state.risk_budget - 0.2)
                recommendations.append(f"Budget reduced due to {drift_name}")
            elif drift["severity"] == "slow_down":
                recommendations.append(f"Consider slowing down: {drift['description']}")
        
        # Budget warnings
        if self.state.risk_budget < 0.3:
            recommendations.append(f"Low budget ({self.state.risk_budget:.2f}) — checkpoint soon")
        
        return PostCheckResult(
            valid=not constraint_violation,
            trust_delta=trust_delta,
            budget_remaining=self.state.risk_budget,
            drift_detected=drift_name,
            recommendations=recommendations,
        )
    
    # =========================================================================
    # HUMAN INTERACTION
    # =========================================================================
    
    def human_interacted(self):
        """Call when human sends a message."""
        self.state.last_human_interaction = datetime.now()
        self.state.trust_score = min(1.0, self.state.trust_score + self.params.trust_boost_interaction)
    
    def human_checkpoint(self):
        """Call when human explicitly confirms/approves."""
        self.state.risk_budget = self.budget_size  # Full reset
        self.state.trust_score = min(1.0, self.state.trust_score + self.params.trust_boost_checkpoint)
        self.state.last_checkpoint = datetime.now()
        self.state.last_human_interaction = datetime.now()
        self.state.total_ops_since_checkpoint = 0
        self.state.warnings_since_checkpoint = 0
    
    def human_corrected(self):
        """Call when human corrects AI output."""
        self.human_interacted()
        # Corrections are healthy in moderation — small penalty if too frequent
        recent_corrections = sum(
            1 for op in list(self.history)[-10:] 
            if op.operation == "_correction"
        )
        if recent_corrections > 3:
            self.state.trust_score = max(0, self.state.trust_score - 0.05)
        
        # Record correction in history
        self.history.append(OperationRecord(
            operation="_correction",
            risk="SAFE",
            timestamp=datetime.now(),
            context_hash="correction",
        ))
    
    def human_approved(self, operation: str = ""):
        """Call when human explicitly approves an action."""
        self.human_checkpoint()
    
    # =========================================================================
    # STATUS & INTROSPECTION
    # =========================================================================
    
    def status(self) -> Dict[str, Any]:
        """Get full anchor status."""
        return {
            "state": self.state.to_dict(),
            "can_proceed_levels": {
                risk: self._can_proceed_for_risk(risk)
                for risk in ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
            },
            "history_size": len(self.history),
            "drift_check": self._detect_drift(),
            "params": self.params.to_dict(),
        }
    
    def can_proceed(self, risk: OperationRisk) -> bool:
        """Quick check: can we proceed with this risk level?"""
        return self._can_proceed_for_risk(risk.value)
    
    def explain(self) -> str:
        """Human-readable explanation of current state."""
        state = self.state
        trust_level = TrustLevel.from_score(state.trust_score)
        
        lines = [
            f"Trust: {trust_level.name} ({state.trust_score:.2f})",
            f"Budget: {state.risk_budget:.2f} / {self.budget_size}",
            f"Ops since checkpoint: {state.total_ops_since_checkpoint}",
            f"Clean streak: {state.consecutive_clean_ops}",
        ]
        
        drift = self._detect_drift()
        if drift:
            lines.append(f"⚠️  Drift: {drift['name']}")
        
        if state.risk_budget < 0.3:
            lines.append("⚠️  Low budget — checkpoint recommended")
        
        return "\n".join(lines)
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _assess_risk(self, operation: str, context: Dict[str, Any]) -> str:
        """Determine risk level of an operation."""
        # Check explicit risk in context
        if "risk_level" in context:
            return context["risk_level"]
        
        # Check for known high-risk indicators
        if context.get("is_external", False):
            return "HIGH"
        if context.get("involves_phi", False):
            return "HIGH"
        if context.get("is_destructive", False):
            return "MEDIUM"
        if context.get("is_write", False):
            return "LOW"
        
        # Check operation name patterns
        op_lower = operation.lower()
        if any(x in op_lower for x in ["delete", "remove", "drop", "truncate"]):
            return "MEDIUM"
        if any(x in op_lower for x in ["write", "update", "create", "insert"]):
            return "LOW"
        if any(x in op_lower for x in ["send", "post", "email", "publish"]):
            return "HIGH"
        if any(x in op_lower for x in ["execute", "run", "eval"]):
            return "MEDIUM"
        
        # Default to SAFE for read-like operations
        return "SAFE"
    
    def _can_proceed_for_risk(self, risk: str) -> bool:
        """Check if we can proceed for a given risk level."""
        cost = RISK_COSTS.get(risk, 1.0)
        min_trust = RISK_TRUST_THRESHOLDS.get(risk, 1.0)
        
        if risk == "CRITICAL":
            return False  # Always requires checkpoint
        
        return (
            self.state.trust_score >= min_trust and
            self.state.risk_budget >= cost
        )
    
    def _detect_drift(self) -> Optional[Dict]:
        """Check for drift patterns in recent history."""
        history_list = list(self.history)
        
        for pattern in DRIFT_PATTERNS:
            try:
                if pattern["detect"](history_list):
                    return {
                        "name": pattern["name"],
                        "description": pattern["description"],
                        "severity": pattern["severity"],
                    }
            except Exception:
                pass  # Skip pattern if detection fails
        
        return None
    
    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Create a simple hash of context for pattern detection."""
        # Just use key parts for comparison
        parts = [
            context.get("operation", ""),
            context.get("path", ""),
            context.get("resource", ""),
            str(context.get("is_external", False)),
        ]
        return ":".join(parts)
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def on_violation(self, callback: Callable[[str, Dict], None]):
        """Register callback for violations."""
        self.violation_callbacks.append(callback)
    
    def _notify_violation(self, violation_type: str, details: Dict):
        """Notify all callbacks of a violation."""
        for callback in self.violation_callbacks:
            try:
                callback(violation_type, details)
            except Exception:
                pass


# =============================================================================
# TUNABLE PARAMETERS
# =============================================================================

@dataclass
class AnchorParams:
    """
    Tunable parameters for anchor behavior.
    
    Adjust these to fine-tune the balance between autonomy and oversight.
    """
    # Trust adjustments
    trust_boost_clean: float = 0.005       # Per clean operation
    trust_boost_streak: float = 0.01       # Bonus for 10+ clean ops
    trust_boost_interaction: float = 0.05  # When human sends message
    trust_boost_checkpoint: float = 0.1    # When human explicitly approves
    trust_penalty_warning: float = 0.02    # Per advisory warning
    trust_penalty_violation: float = 0.2   # Per constraint violation
    
    # Time limits
    max_minutes_without_human: int = 60    # After this, MEDIUM+ ops need checkpoint
    
    # Drift detection
    drift_window_size: int = 20            # Ops to consider for drift
    speed_threshold_per_minute: int = 60   # Ops/minute before speed drift
    
    def to_dict(self) -> Dict:
        return {
            "trust_boost_clean": self.trust_boost_clean,
            "trust_boost_streak": self.trust_boost_streak,
            "trust_boost_interaction": self.trust_boost_interaction,
            "trust_boost_checkpoint": self.trust_boost_checkpoint,
            "trust_penalty_warning": self.trust_penalty_warning,
            "trust_penalty_violation": self.trust_penalty_violation,
            "max_minutes_without_human": self.max_minutes_without_human,
            "drift_window_size": self.drift_window_size,
            "speed_threshold_per_minute": self.speed_threshold_per_minute,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global anchor instance
_global_anchor: Optional[SmartAnchor] = None


def get_anchor() -> SmartAnchor:
    """Get or create global anchor."""
    global _global_anchor
    if _global_anchor is None:
        _global_anchor = SmartAnchor()
    return _global_anchor


def reset_anchor():
    """Reset global anchor."""
    global _global_anchor
    _global_anchor = SmartAnchor()


def check_operation(operation: str, context: Dict[str, Any]) -> PreCheckResult:
    """Quick check using global anchor."""
    return get_anchor().pre_operation(operation, context)


def record_operation(
    operation: str, 
    context: Dict[str, Any], 
    warnings: int = 0,
    violation: bool = False,
) -> PostCheckResult:
    """Record operation using global anchor."""
    return get_anchor().post_operation(operation, context, warnings, violation)


def human_here():
    """Signal human interaction on global anchor."""
    get_anchor().human_interacted()


def human_approved():
    """Signal human approval on global anchor."""
    get_anchor().human_approved()


def anchor_status() -> Dict[str, Any]:
    """Get status of global anchor."""
    return get_anchor().status()
