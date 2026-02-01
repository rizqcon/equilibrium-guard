"""
Equilibrium Guard
=================

Compliance-aware constraint validation and human-AI alignment tracking.

Patterns distilled from S.I.S. (Sovereign Intelligence System).
Adapted for AI execution compliance requirements.

Core Components:
- Constraint/ConstraintValidator: Define and validate compliance rules
- SmartAnchor: Risk-weighted autonomy with drift detection
- create_compliance_validator: Pre-built SOC2/HIPAA/CIS constraints

Quick Start:
    from equilibrium_guard import EquilibriumGuard
    
    guard = EquilibriumGuard()
    guard.on_human_message()
    
    can_proceed, issues = guard.pre_check("file_write", {"path": "/data/x.json"})
    if can_proceed:
        write_file()
        guard.post_record("file_write", context)
"""

__version__ = "0.1.0"
__author__ = "Alberto Ramos-Izquierdo"

# Core constraint system
from .constraint import (
    Constraint,
    ConstraintSeverity,
    ConstraintValidator,
    ConstraintViolation,
    ValidationResult,
    guarded,
    ComplianceFramework,
)

# Smart anchor system
from .anchor import (
    SmartAnchor,
    AnchorParams,
    AnchorState,
    OperationRisk,
    TrustLevel,
    PreCheckResult,
    PostCheckResult,
    # Convenience functions
    get_anchor,
    reset_anchor,
    check_operation,
    record_operation,
    human_here,
    human_approved,
    anchor_status,
)

# Pre-built compliance constraints
from .compliance_map import (
    create_compliance_validator,
    create_soc2_constraints,
    create_hipaa_constraints,
    create_cis_constraints,
    create_custom_constraints,
)

# High-level integration
from .guard import EquilibriumGuard

__all__ = [
    # Version
    "__version__",
    # Constraints
    "Constraint",
    "ConstraintSeverity",
    "ConstraintValidator",
    "ConstraintViolation",
    "ValidationResult",
    "guarded",
    "ComplianceFramework",
    # Anchor
    "SmartAnchor",
    "AnchorParams",
    "AnchorState",
    "OperationRisk",
    "TrustLevel",
    "PreCheckResult",
    "PostCheckResult",
    "get_anchor",
    "reset_anchor",
    "check_operation",
    "record_operation",
    "human_here",
    "human_approved",
    "anchor_status",
    # Compliance
    "create_compliance_validator",
    "create_soc2_constraints",
    "create_hipaa_constraints",
    "create_cis_constraints",
    "create_custom_constraints",
    # Integration
    "EquilibriumGuard",
]
