"""
Equilibrium Guard - Constraint Validator
=========================================

Core pattern: Operations that violate constraints CANNOT execute.
Not "blocked by policy" — rejected by the validator itself.

This is the "can't vs shouldn't" distinction.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum, auto
from datetime import datetime


class ConstraintSeverity(Enum):
    """How critical is this constraint?"""
    ADVISORY = auto()      # Log warning, allow execution
    REQUIRED = auto()      # Block execution, allow override with justification
    MANDATORY = auto()     # Block execution, no override possible


class ComplianceFramework(Enum):
    """Which compliance framework does this constraint serve?"""
    SOC2 = "soc2"
    HIPAA = "hipaa"
    CIS = "cis"
    INTERNAL = "internal"  # RIZQ-specific rules


@dataclass
class Constraint:
    """
    A single constraint that must be satisfied for an operation to proceed.
    
    The key insight: constraints are checked BEFORE execution.
    If any mandatory constraint fails, the operation is rejected.
    """
    id: str
    name: str
    description: str
    check: Callable[[Dict[str, Any]], bool]  # Returns True if constraint satisfied
    severity: ConstraintSeverity = ConstraintSeverity.REQUIRED
    frameworks: List[ComplianceFramework] = field(default_factory=list)
    error_message: str = ""
    
    def evaluate(self, context: Dict[str, Any]) -> 'ConstraintResult':
        """Evaluate this constraint against the given context."""
        try:
            satisfied = self.check(context)
            return ConstraintResult(
                constraint_id=self.id,
                satisfied=satisfied,
                severity=self.severity,
                message=None if satisfied else (self.error_message or f"Constraint '{self.name}' not satisfied"),
                evaluated_at=datetime.now(),
            )
        except Exception as e:
            return ConstraintResult(
                constraint_id=self.id,
                satisfied=False,
                severity=self.severity,
                message=f"Constraint evaluation error: {str(e)}",
                evaluated_at=datetime.now(),
            )


@dataclass
class ConstraintResult:
    """Result of evaluating a single constraint."""
    constraint_id: str
    satisfied: bool
    severity: ConstraintSeverity
    message: Optional[str]
    evaluated_at: datetime


@dataclass
class ValidationResult:
    """
    Result of validating an operation against all applicable constraints.
    
    Key property: can_execute
    - True only if ALL mandatory constraints pass
    - Required constraints can be overridden with justification
    - Advisory constraints just log warnings
    """
    operation: str
    results: List[ConstraintResult]
    override_justification: Optional[str] = None
    
    @property
    def mandatory_failures(self) -> List[ConstraintResult]:
        return [r for r in self.results 
                if not r.satisfied and r.severity == ConstraintSeverity.MANDATORY]
    
    @property
    def required_failures(self) -> List[ConstraintResult]:
        return [r for r in self.results 
                if not r.satisfied and r.severity == ConstraintSeverity.REQUIRED]
    
    @property
    def advisory_failures(self) -> List[ConstraintResult]:
        return [r for r in self.results 
                if not r.satisfied and r.severity == ConstraintSeverity.ADVISORY]
    
    @property
    def can_execute(self) -> bool:
        """
        The core question: CAN this operation proceed?
        
        - Any MANDATORY failure = hard no
        - REQUIRED failures can be overridden with justification
        - ADVISORY failures are just warnings
        """
        # Mandatory failures are absolute blocks
        if self.mandatory_failures:
            return False
        
        # Required failures need justification to proceed
        if self.required_failures and not self.override_justification:
            return False
        
        return True
    
    @property
    def warnings(self) -> List[str]:
        """Collect all warning messages."""
        msgs = []
        for r in self.advisory_failures:
            msgs.append(f"[ADVISORY] {r.message}")
        if self.required_failures and self.override_justification:
            for r in self.required_failures:
                msgs.append(f"[OVERRIDDEN] {r.message} — Justification: {self.override_justification}")
        return msgs
    
    @property
    def blocking_errors(self) -> List[str]:
        """Collect all blocking error messages."""
        msgs = []
        for r in self.mandatory_failures:
            msgs.append(f"[MANDATORY] {r.message}")
        if self.required_failures and not self.override_justification:
            for r in self.required_failures:
                msgs.append(f"[REQUIRED] {r.message}")
        return msgs


class ConstraintValidator:
    """
    The constraint validator.
    
    Register constraints, then validate operations against them.
    Operations that fail validation CANNOT execute.
    """
    
    def __init__(self):
        self.constraints: Dict[str, Constraint] = {}
        self.operation_constraints: Dict[str, List[str]] = {}  # operation -> constraint_ids
        self.history: List[ValidationResult] = []
    
    def register(self, constraint: Constraint, operations: List[str] = None):
        """
        Register a constraint.
        
        If operations specified, constraint only applies to those operations.
        If operations is None, constraint applies to ALL operations.
        """
        self.constraints[constraint.id] = constraint
        
        if operations:
            for op in operations:
                if op not in self.operation_constraints:
                    self.operation_constraints[op] = []
                self.operation_constraints[op].append(constraint.id)
    
    def get_applicable_constraints(self, operation: str) -> List[Constraint]:
        """Get all constraints that apply to this operation."""
        # Global constraints (no specific operations)
        global_ids = [
            cid for cid, c in self.constraints.items()
            if cid not in [
                item for sublist in self.operation_constraints.values() 
                for item in sublist
            ]
        ]
        
        # Operation-specific constraints
        specific_ids = self.operation_constraints.get(operation, [])
        
        all_ids = set(global_ids + specific_ids)
        return [self.constraints[cid] for cid in all_ids if cid in self.constraints]
    
    def validate(
        self, 
        operation: str, 
        context: Dict[str, Any],
        override_justification: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate an operation against all applicable constraints.
        
        This is the core function. Call this BEFORE executing any sensitive operation.
        If result.can_execute is False, DO NOT PROCEED.
        """
        constraints = self.get_applicable_constraints(operation)
        results = [c.evaluate(context) for c in constraints]
        
        validation = ValidationResult(
            operation=operation,
            results=results,
            override_justification=override_justification,
        )
        
        self.history.append(validation)
        return validation
    
    def must_execute(
        self,
        operation: str,
        context: Dict[str, Any],
        override_justification: Optional[str] = None,
    ) -> bool:
        """
        Convenience method: validate and return simple bool.
        
        Use when you just need a yes/no answer.
        For detailed results, use validate() instead.
        """
        return self.validate(operation, context, override_justification).can_execute


# =============================================================================
# DECORATOR PATTERN
# =============================================================================

def guarded(validator: ConstraintValidator, operation: str):
    """
    Decorator to guard a function with constraint validation.
    
    Usage:
        @guarded(validator, "file_access")
        def read_sensitive_file(path: str):
            ...
    
    The decorated function will only execute if constraints pass.
    If constraints fail, raises ConstraintViolation.
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Build context from function arguments
            context = {"args": args, "kwargs": kwargs, "function": func.__name__}
            
            result = validator.validate(operation, context)
            
            if not result.can_execute:
                raise ConstraintViolation(
                    operation=operation,
                    errors=result.blocking_errors,
                )
            
            # Log warnings if any
            for warning in result.warnings:
                print(f"⚠️  {warning}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


class ConstraintViolation(Exception):
    """Raised when an operation violates constraints and cannot proceed."""
    
    def __init__(self, operation: str, errors: List[str]):
        self.operation = operation
        self.errors = errors
        super().__init__(f"Operation '{operation}' blocked: {'; '.join(errors)}")
