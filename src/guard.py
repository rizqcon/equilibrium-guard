"""
Equilibrium Guard - High-Level Integration
==========================================

Combines constraint validation and smart anchor into a single interface.
"""

from typing import Dict, Any, List, Tuple, Optional
from .constraint import ConstraintValidator
from .anchor import SmartAnchor
from .compliance_map import create_compliance_validator


class EquilibriumGuard:
    """
    High-level integration layer combining constraints and anchor.
    
    Usage:
        guard = EquilibriumGuard()
        
        # Human interaction
        guard.on_human_message()
        
        # Before operation
        can_proceed, issues = guard.pre_check("file_write", context)
        
        if can_proceed:
            do_operation()
            guard.post_record("file_write", context)
        else:
            report_blocked(issues)
    """
    
    def __init__(
        self,
        validator: Optional[ConstraintValidator] = None,
        anchor: Optional[SmartAnchor] = None,
        initial_trust: float = 0.7,
        load_compliance: bool = True,
    ):
        """
        Initialize the guard.
        
        Args:
            validator: Custom validator, or None to create default
            anchor: Custom anchor, or None to create default
            initial_trust: Starting trust score (0.0 - 1.0)
            load_compliance: If True, load SOC2/HIPAA/CIS/RIZQ constraints
        """
        if validator is not None:
            self.validator = validator
        elif load_compliance:
            self.validator = create_compliance_validator()
        else:
            self.validator = ConstraintValidator()
        
        self.anchor = anchor or SmartAnchor(initial_trust=initial_trust)
    
    def pre_check(
        self,
        operation: str,
        context: Dict[str, Any],
        override_justification: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Pre-operation check. Call BEFORE executing any operation.
        
        Args:
            operation: Name/type of operation
            context: Operation context (path, user, flags, etc.)
            override_justification: Justification for overriding REQUIRED constraints
        
        Returns:
            Tuple of (can_proceed, issues_or_warnings)
            - If can_proceed is False, issues contains blocking errors
            - If can_proceed is True, issues may contain warnings
        """
        issues = []
        warnings = []
        
        # 1. Anchor pre-check (risk budget + trust)
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
        
        can_proceed = len(issues) == 0
        return can_proceed, issues if issues else warnings
    
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
        
        Args:
            operation: Name/type of operation
            context: Operation context
            advisory_warnings: Number of advisory warnings triggered
            constraint_violation: Whether a constraint was violated
        
        Returns:
            Dict with validation results and recommendations
        """
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
    
    def on_human_approval(self):
        """Call when human explicitly approves/confirms an action."""
        self.anchor.human_checkpoint()
    
    def on_human_correction(self):
        """Call when human corrects AI output."""
        self.anchor.human_corrected()
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def status(self) -> Dict[str, Any]:
        """Get full guard status."""
        return {
            "anchor": self.anchor.status(),
            "explanation": self.anchor.explain(),
            "constraints_registered": len(self.validator.constraints),
        }
    
    def explain(self) -> str:
        """Get human-readable explanation of current state."""
        return self.anchor.explain()
    
    # =========================================================================
    # CONSTRAINT MANAGEMENT
    # =========================================================================
    
    def register_constraint(self, constraint, operations: List[str] = None):
        """
        Register an additional constraint.
        
        Args:
            constraint: Constraint object to register
            operations: If specified, constraint only applies to these operations
        """
        self.validator.register(constraint, operations)
    
    @property
    def can_proceed_levels(self) -> Dict[str, bool]:
        """Get which risk levels can currently proceed."""
        return self.anchor.status()["can_proceed_levels"]
