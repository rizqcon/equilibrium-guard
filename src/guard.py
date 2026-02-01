"""
Equilibrium Guard - High-Level Integration
==========================================

Zero-trust security layer for AI agents.
Combines constraint validation and smart anchor into a single interface.

Modes:
- disabled: No checks, pass everything
- shadow: Log decisions but don't block (learning mode)
- soft: Block HIGH/CRITICAL only, shadow the rest
- enforce: Full enforcement
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from .constraint import ConstraintValidator
from .anchor import SmartAnchor, OperationRisk
from .compliance_map import create_compliance_validator


class GuardMode(Enum):
    """Operating modes for the guard."""
    DISABLED = "disabled"   # No checks
    SHADOW = "shadow"       # Log only, don't block
    SOFT = "soft"           # Block HIGH/CRITICAL, shadow rest
    ENFORCE = "enforce"     # Full enforcement


@dataclass
class Decision:
    """Record of a guard decision."""
    timestamp: datetime
    operation: str
    mode: str
    risk_level: str
    would_block: bool
    actually_blocked: bool
    reasons: List[str]
    context_summary: Dict[str, Any]
    trust_score: float
    budget_remaining: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "operation": self.operation,
            "mode": self.mode,
            "risk_level": self.risk_level,
            "would_block": self.would_block,
            "actually_blocked": self.actually_blocked,
            "reasons": self.reasons,
            "context_summary": self.context_summary,
            "trust_score": self.trust_score,
            "budget_remaining": self.budget_remaining,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class GuardMetrics:
    """Metrics tracking for the guard."""
    total_checks: int = 0
    would_block_count: int = 0
    actually_blocked_count: int = 0
    shadow_passes: int = 0  # Would block but allowed due to shadow/soft mode
    by_risk_level: Dict[str, int] = field(default_factory=lambda: {
        "SAFE": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0
    })
    by_operation: Dict[str, int] = field(default_factory=dict)
    trust_score_samples: List[float] = field(default_factory=list)
    budget_samples: List[float] = field(default_factory=list)
    
    def record(self, decision: Decision):
        """Record a decision in metrics."""
        self.total_checks += 1
        
        if decision.would_block:
            self.would_block_count += 1
        
        if decision.actually_blocked:
            self.actually_blocked_count += 1
        elif decision.would_block:
            self.shadow_passes += 1
        
        if decision.risk_level in self.by_risk_level:
            self.by_risk_level[decision.risk_level] += 1
        
        if decision.operation not in self.by_operation:
            self.by_operation[decision.operation] = 0
        self.by_operation[decision.operation] += 1
        
        self.trust_score_samples.append(decision.trust_score)
        self.budget_samples.append(decision.budget_remaining)
        
        # Keep only last 1000 samples
        if len(self.trust_score_samples) > 1000:
            self.trust_score_samples = self.trust_score_samples[-1000:]
            self.budget_samples = self.budget_samples[-1000:]
    
    def summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_checks": self.total_checks,
            "would_block_count": self.would_block_count,
            "actually_blocked_count": self.actually_blocked_count,
            "shadow_passes": self.shadow_passes,
            "block_rate": self.would_block_count / max(1, self.total_checks),
            "effective_block_rate": self.actually_blocked_count / max(1, self.total_checks),
            "by_risk_level": self.by_risk_level,
            "top_operations": dict(sorted(
                self.by_operation.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]),
            "avg_trust_score": sum(self.trust_score_samples) / max(1, len(self.trust_score_samples)),
            "avg_budget": sum(self.budget_samples) / max(1, len(self.budget_samples)),
        }


class EquilibriumGuard:
    """
    Zero-trust security layer for AI agents.
    
    Modes:
        disabled: No checks, everything passes
        shadow: Log what would happen, don't block (learning mode)
        soft: Block HIGH/CRITICAL only, shadow SAFE/LOW/MEDIUM
        enforce: Full enforcement
    
    Usage:
        guard = EquilibriumGuard(mode=GuardMode.SHADOW)
        
        # Human interaction
        guard.on_human_message()
        
        # Before operation
        can_proceed, issues = guard.pre_check("file_write", context)
        
        if can_proceed:
            do_operation()
            guard.post_record("file_write", context)
        else:
            report_blocked(issues)
        
        # Review what's happening
        print(guard.metrics.summary())
        print(guard.recent_decisions())
    """
    
    def __init__(
        self,
        mode: GuardMode = GuardMode.SHADOW,
        validator: Optional[ConstraintValidator] = None,
        anchor: Optional[SmartAnchor] = None,
        initial_trust: float = 0.7,
        load_compliance: bool = True,
        log_decisions: bool = True,
        max_decision_history: int = 1000,
    ):
        """
        Initialize the guard.
        
        Args:
            mode: Operating mode (disabled/shadow/soft/enforce)
            validator: Custom validator, or None to create default
            anchor: Custom anchor, or None to create default
            initial_trust: Starting trust score (0.0 - 1.0)
            load_compliance: If True, load SOC2/HIPAA/CIS constraints
            log_decisions: If True, keep decision history
            max_decision_history: Max decisions to keep in memory
        """
        self.mode = mode
        self.log_decisions = log_decisions
        self.max_decision_history = max_decision_history
        
        if validator is not None:
            self.validator = validator
        elif load_compliance:
            self.validator = create_compliance_validator()
        else:
            self.validator = ConstraintValidator()
        
        self.anchor = anchor or SmartAnchor(initial_trust=initial_trust)
        self.metrics = GuardMetrics()
        self.decision_history: List[Decision] = []
        self._decision_callbacks: List[callable] = []
    
    # =========================================================================
    # MODE MANAGEMENT
    # =========================================================================
    
    def set_mode(self, mode: GuardMode):
        """Change operating mode."""
        old_mode = self.mode
        self.mode = mode
        self._log_event("mode_change", {"from": old_mode.value, "to": mode.value})
    
    def disable(self):
        """Kill switch — disable all checks."""
        self.set_mode(GuardMode.DISABLED)
    
    def enable_shadow(self):
        """Enter learning mode."""
        self.set_mode(GuardMode.SHADOW)
    
    def enable_soft(self):
        """Enable soft enforcement (HIGH/CRITICAL only)."""
        self.set_mode(GuardMode.SOFT)
    
    def enable_enforce(self):
        """Enable full enforcement."""
        self.set_mode(GuardMode.ENFORCE)
    
    # =========================================================================
    # CORE API
    # =========================================================================
    
    def pre_check(
        self,
        operation: str,
        context: Dict[str, Any],
        override_justification: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Pre-operation check. Call BEFORE executing any operation.
        
        Returns (can_proceed, issues_or_warnings) based on current mode.
        """
        # Disabled mode — always pass
        if self.mode == GuardMode.DISABLED:
            return True, []
        
        issues = []
        warnings = []
        
        # Get risk level
        risk_level = self._get_risk_level(operation, context)
        
        # 1. Anchor pre-check
        anchor_check = self.anchor.pre_operation(operation, context)
        if not anchor_check.can_proceed:
            issues.append(f"[ANCHOR] {anchor_check.reason}")
        warnings.extend(anchor_check.warnings)
        
        # 2. Compliance validation
        compliance_result = self.validator.validate(
            operation, 
            context, 
            override_justification
        )
        if not compliance_result.can_execute:
            issues.extend(compliance_result.blocking_errors)
        warnings.extend(compliance_result.warnings)
        
        # Determine if we would block
        would_block = len(issues) > 0
        
        # Determine if we actually block (based on mode)
        actually_block = self._should_actually_block(would_block, risk_level)
        
        # Record decision
        decision = Decision(
            timestamp=datetime.now(),
            operation=operation,
            mode=self.mode.value,
            risk_level=risk_level,
            would_block=would_block,
            actually_blocked=actually_block,
            reasons=issues if issues else warnings,
            context_summary=self._summarize_context(context),
            trust_score=self.anchor.state.trust_score,
            budget_remaining=self.anchor.state.risk_budget,
        )
        
        self._record_decision(decision)
        
        # Return based on actual blocking decision
        if actually_block:
            return False, issues
        else:
            return True, warnings
    
    def post_record(
        self,
        operation: str,
        context: Dict[str, Any],
        advisory_warnings: int = 0,
        constraint_violation: bool = False,
    ) -> Dict[str, Any]:
        """
        Post-operation record. Call AFTER executing an operation.
        
        Records the operation and adjusts trust/budget accordingly.
        """
        if self.mode == GuardMode.DISABLED:
            return {"valid": True, "budget_remaining": 1.0, "trust_delta": 0}
        
        post = self.anchor.post_operation(
            operation,
            context,
            advisory_warnings,
            constraint_violation,
        )
        
        return {
            "valid": post.valid,
            "budget_remaining": post.budget_remaining,
            "trust_delta": post.trust_delta,
            "drift_detected": post.drift_detected,
            "recommendations": post.recommendations,
        }
    
    # =========================================================================
    # HUMAN INTERACTION
    # =========================================================================
    
    def on_human_message(self):
        """Call when human sends a message."""
        self.anchor.human_interacted()
        self._log_event("human_message", {})
    
    def on_human_approval(self):
        """Call when human explicitly approves/confirms an action."""
        self.anchor.human_checkpoint()
        self._log_event("human_approval", {})
    
    def on_human_correction(self):
        """Call when human corrects AI output."""
        self.anchor.human_corrected()
        self._log_event("human_correction", {})
    
    # =========================================================================
    # OBSERVABILITY
    # =========================================================================
    
    def status(self) -> Dict[str, Any]:
        """Get full guard status."""
        return {
            "mode": self.mode.value,
            "anchor": self.anchor.status(),
            "metrics": self.metrics.summary(),
            "constraints_registered": len(self.validator.constraints),
        }
    
    def explain(self) -> str:
        """Get human-readable explanation of current state."""
        lines = [
            f"Mode: {self.mode.value.upper()}",
            self.anchor.explain(),
            f"Checks: {self.metrics.total_checks} total, {self.metrics.would_block_count} would-block, {self.metrics.actually_blocked_count} blocked",
        ]
        if self.metrics.shadow_passes > 0:
            lines.append(f"Shadow passes: {self.metrics.shadow_passes} (would block but allowed)")
        return "\n".join(lines)
    
    def recent_decisions(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent decision history."""
        return [d.to_dict() for d in self.decision_history[-n:]]
    
    def decisions_summary(self) -> str:
        """Get human-readable summary of recent decisions."""
        if not self.decision_history:
            return "No decisions recorded yet."
        
        lines = ["Recent decisions:"]
        for d in self.decision_history[-10:]:
            status = "🚫 BLOCKED" if d.actually_blocked else ("⚠️ WOULD-BLOCK" if d.would_block else "✅ PASS")
            lines.append(f"  {d.timestamp.strftime('%H:%M:%S')} {d.operation} [{d.risk_level}] {status}")
        
        return "\n".join(lines)
    
    def on_decision(self, callback: callable):
        """Register callback for each decision (for real-time logging)."""
        self._decision_callbacks.append(callback)
    
    # =========================================================================
    # CONSTRAINT MANAGEMENT
    # =========================================================================
    
    def register_constraint(self, constraint, operations: List[str] = None):
        """Register an additional constraint."""
        self.validator.register(constraint, operations)
    
    @property
    def can_proceed_levels(self) -> Dict[str, bool]:
        """Get which risk levels can currently proceed."""
        if self.mode == GuardMode.DISABLED:
            return {risk: True for risk in ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]}
        return self.anchor.status()["can_proceed_levels"]
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _should_actually_block(self, would_block: bool, risk_level: str) -> bool:
        """Determine if we should actually block based on mode."""
        if not would_block:
            return False
        
        if self.mode == GuardMode.DISABLED:
            return False
        elif self.mode == GuardMode.SHADOW:
            return False  # Never block in shadow mode
        elif self.mode == GuardMode.SOFT:
            # Only block HIGH and CRITICAL
            return risk_level in ["HIGH", "CRITICAL"]
        else:  # ENFORCE
            return True
    
    def _get_risk_level(self, operation: str, context: Dict[str, Any]) -> str:
        """Get risk level for an operation."""
        # Check explicit risk in context
        if "risk_level" in context:
            return context["risk_level"]
        
        # Use anchor's assessment
        return self.anchor._assess_risk(operation, context)
    
    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a safe summary of context for logging."""
        safe_keys = ["operation", "risk_level", "path", "resource", "is_external", 
                     "is_write", "is_destructive", "user_id"]
        return {k: v for k, v in context.items() if k in safe_keys}
    
    def _record_decision(self, decision: Decision):
        """Record a decision."""
        # Update metrics
        self.metrics.record(decision)
        
        # Store in history
        if self.log_decisions:
            self.decision_history.append(decision)
            if len(self.decision_history) > self.max_decision_history:
                self.decision_history = self.decision_history[-self.max_decision_history:]
        
        # Notify callbacks
        for callback in self._decision_callbacks:
            try:
                callback(decision)
            except Exception:
                pass
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a guard event."""
        # For now, just track. Could extend to external logging.
        pass


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_guard(
    mode: str = "shadow",
    initial_trust: float = 0.7,
    load_compliance: bool = True,
) -> EquilibriumGuard:
    """
    Create a guard with sensible defaults.
    
    Args:
        mode: "disabled", "shadow", "soft", or "enforce"
        initial_trust: Starting trust score
        load_compliance: Load SOC2/HIPAA/CIS constraints
    """
    mode_enum = GuardMode(mode)
    return EquilibriumGuard(
        mode=mode_enum,
        initial_trust=initial_trust,
        load_compliance=load_compliance,
    )
