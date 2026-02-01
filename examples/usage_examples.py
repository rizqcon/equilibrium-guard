"""
Equilibrium Guard - Usage Examples
===================================

READ-ONLY EXAMPLES. Do not run this file.
These demonstrate how the patterns would be used in practice.
"""

# =============================================================================
# EXAMPLE 1: Basic Constraint Validation
# =============================================================================

"""
from constraint import Constraint, ConstraintSeverity, ConstraintValidator

# Create validator
validator = ConstraintValidator()

# Register a simple constraint
validator.register(
    Constraint(
        id="auth_required",
        name="Authentication Required",
        description="User must be authenticated",
        check=lambda ctx: ctx.get("user_authenticated", False),
        severity=ConstraintSeverity.MANDATORY,
        error_message="Access denied - not authenticated",
    )
)

# Validate an operation
context = {
    "user_authenticated": False,
    "resource": "/api/sensitive-data",
}

result = validator.validate("data_access", context)

if result.can_execute:
    # Proceed with operation
    fetch_sensitive_data()
else:
    # Operation blocked
    print(f"Blocked: {result.blocking_errors}")
    # Output: Blocked: ['[MANDATORY] Access denied - not authenticated']
"""


# =============================================================================
# EXAMPLE 2: Compliance-Aware File Access
# =============================================================================

"""
from compliance_map import create_compliance_validator

validator = create_compliance_validator()

# Context for a file operation
context = {
    "operation": "file_read",
    "path": "/home/rizqdev/projects/client-data/records.json",
    "user_authenticated": True,
    "user_id": "jarvis-ai",
    "involves_phi": True,
    "phi_authorization": True,
    "user_role": "ai_assistant",
    "authorized_roles": ["ai_assistant", "admin"],
    "phi_audit_enabled": True,
    "tls_enabled": True,
    "integrity_controls": True,
    "authorized_paths": ["/home/rizqdev/projects/"],
}

result = validator.validate("file_read", context)

if result.can_execute:
    # All SOC2, HIPAA, CIS, and RIZQ constraints passed
    read_file(context["path"])
else:
    # Which frameworks blocked us?
    for error in result.blocking_errors:
        print(error)
"""


# =============================================================================
# EXAMPLE 3: Using the Decorator Pattern
# =============================================================================

"""
from constraint import guarded, ConstraintValidator, Constraint, ConstraintSeverity

validator = ConstraintValidator()

validator.register(
    Constraint(
        id="path_check",
        name="Path Authorization",
        check=lambda ctx: ctx["kwargs"]["path"].startswith("/safe/"),
        severity=ConstraintSeverity.MANDATORY,
    )
)

@guarded(validator, "file_delete")
def delete_file(path: str):
    os.remove(path)

# This will work
delete_file("/safe/temp/old-file.txt")

# This will raise ConstraintViolation
delete_file("/etc/passwd")  # Blocked!
"""


# =============================================================================
# EXAMPLE 4: Smart Anchor for AI Operations
# =============================================================================

"""
from anchor import SmartAnchor, OperationRisk

anchor = SmartAnchor(initial_trust=0.7)

# Human just sent a message
anchor.human_interacted()

# Before any operation: pre-check
context = {
    "operation": "send_email",
    "is_external": True,
    "recipient": "client@example.com",
}

check = anchor.pre_operation("send_email", context)

if not check.can_proceed:
    # Blocked — ask human
    print(f"Blocked: {check.reason}")
    ask_human("Can I send this email to the client?")
else:
    # Proceed
    send_external_email()
    
    # After operation: record it
    post = anchor.post_operation("send_email", context, advisory_warnings=0)
    
    if post.drift_detected:
        print(f"Drift warning: {post.drift_detected}")
    
    print(f"Budget remaining: {post.budget_remaining}")

# Human explicitly approves — resets budget, boosts trust
anchor.human_checkpoint()

# Show current status
print(anchor.explain())
# Trust: COLLABORATIVE (0.75)
# Budget: 1.00 / 1.0
# Ops since checkpoint: 0
# Clean streak: 0

# Full status dict
print(anchor.status())
# {
#     "state": {
#         "risk_budget": 1.0,
#         "trust_score": 0.75,
#         "trust_level": "COLLABORATIVE",
#         ...
#     },
#     "can_proceed_levels": {
#         "SAFE": true,
#         "LOW": true,
#         "MEDIUM": true,
#         "HIGH": true,
#         "CRITICAL": false  # Always requires checkpoint
#     },
#     "drift_check": null,
#     ...
# }
"""


# =============================================================================
# EXAMPLE 5: Combining Constraints + Smart Anchor
# =============================================================================

"""
from constraint import ConstraintValidator, Constraint, ConstraintSeverity
from anchor import SmartAnchor, OperationRisk

validator = ConstraintValidator()
anchor = SmartAnchor()

# Constraint that checks anchor status
validator.register(
    Constraint(
        id="anchor_check",
        name="Human Alignment Check",
        description="AI must be anchored to human oversight for risky ops",
        check=lambda ctx: anchor.can_proceed(
            OperationRisk[ctx.get("risk_level", "SAFE")]
        ),
        severity=ConstraintSeverity.MANDATORY,
        error_message="AI autonomy budget depleted or trust too low",
    )
)

# Now validation includes alignment check
context = {
    "operation": "external_api_call",
    "risk_level": "HIGH",
    "user_authenticated": True,
    "is_external": True,
}

result = validator.validate("api_call", context)

if not result.can_execute:
    # Either compliance failed OR anchor failed
    print(result.blocking_errors)
else:
    # Execute and record
    do_api_call()
    anchor.post_operation("api_call", context)
"""


# =============================================================================
# EXAMPLE 6: Override with Justification
# =============================================================================

"""
from compliance_map import create_compliance_validator

validator = create_compliance_validator()

context = {
    "operation": "data_export",
    "is_sensitive": True,
    "need_to_know_justified": False,  # Would normally fail CIS 3.3
}

# First attempt - blocked
result = validator.validate("data_export", context)
print(result.can_execute)  # False
print(result.blocking_errors)  # CIS 3.3 violation

# With justification - REQUIRED constraints can be overridden
result = validator.validate(
    "data_export", 
    context,
    override_justification="Emergency audit request from auditor@rizq.tech, ticket #12345"
)
print(result.can_execute)  # True (if CIS 3.3 is REQUIRED, not MANDATORY)
print(result.warnings)     # Shows the override was logged
"""


# =============================================================================
# EXAMPLE 7: Real-World Integration (OpenClaw Guardrails)
# =============================================================================

"""
# This is how it would integrate with OpenClaw's existing guardrail system

from typing import Dict, Any, List, Tuple
from compliance_map import create_compliance_validator
from anchor import SmartAnchor

class EquilibriumGuard:
    '''
    OpenClaw integration layer.
    
    Wraps the constraint validator and smart anchor into
    a single interface for the agent runtime.
    '''
    
    def __init__(self):
        self.validator = create_compliance_validator()
        self.anchor = SmartAnchor(initial_trust=0.7)
    
    def pre_check(
        self, 
        operation: str, 
        context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        '''
        Pre-operation check. Call BEFORE executing.
        
        Returns (can_proceed, reasons_if_not)
        '''
        issues = []
        
        # 1. Anchor pre-check (risk budget + trust)
        anchor_check = self.anchor.pre_operation(operation, context)
        if not anchor_check.can_proceed:
            issues.append(f"[ANCHOR] {anchor_check.reason}")
        
        # 2. Compliance validation
        compliance_result = self.validator.validate(operation, context)
        if not compliance_result.can_execute:
            issues.extend(compliance_result.blocking_errors)
        
        can_proceed = len(issues) == 0
        
        # Collect warnings even if proceeding
        warnings = anchor_check.warnings + compliance_result.warnings
        
        return can_proceed, issues if issues else warnings
    
    def post_record(
        self,
        operation: str,
        context: Dict[str, Any],
        advisory_warnings: int = 0,
        constraint_violation: bool = False,
    ) -> Dict[str, Any]:
        '''
        Post-operation record. Call AFTER executing.
        
        Records the operation and adjusts trust/budget.
        '''
        post = self.anchor.post_operation(
            operation, 
            context, 
            advisory_warnings, 
            constraint_violation
        )
        
        return {
            "valid": post.valid,
            "budget_remaining": post.budget_remaining,
            "trust_delta": post.trust_delta,
            "drift_detected": post.drift_detected,
            "recommendations": post.recommendations,
        }
    
    def on_human_message(self):
        '''Call when human sends a message.'''
        self.anchor.human_interacted()
    
    def on_human_approval(self):
        '''Call when human explicitly approves/confirms.'''
        self.anchor.human_checkpoint()
    
    def on_human_correction(self):
        '''Call when human corrects AI output.'''
        self.anchor.human_corrected()
    
    def status(self) -> Dict[str, Any]:
        '''Get full guard status.'''
        return {
            "anchor": self.anchor.status(),
            "explanation": self.anchor.explain(),
        }


# Usage in agent runtime:
guard = EquilibriumGuard()

# Human sends message — update anchor
guard.on_human_message()

# Before any tool call
can_proceed, issues = guard.pre_check("file_write", {
    "path": "/home/rizqdev/projects/taskboard/data.json",
    "user_authenticated": True,
    "user_id": "jarvis",
    "is_write": True,
})

if can_proceed:
    # Execute
    result = execute_tool("file_write", ...)
    
    # Record (adjusts trust/budget)
    post = guard.post_record("file_write", context)
    
    if post["drift_detected"]:
        log_warning(f"Drift: {post['drift_detected']}")
    
    if post["recommendations"]:
        for rec in post["recommendations"]:
            log_info(rec)
else:
    report_to_human(f"Blocked: {issues}")

# After dozens of safe operations...
print(guard.status())
# Shows accumulated trust, remaining budget, any drift warnings
"""


# =============================================================================
# SUMMARY
# =============================================================================

"""
Key Patterns:

1. CONSTRAINT VALIDATION
   - Define rules as Constraint objects
   - Validate operations BEFORE execution
   - Operations that fail validation CANNOT execute
   - Severity levels: ADVISORY (warn), REQUIRED (block, overridable), MANDATORY (hard block)

2. COMPLIANCE MAPPING
   - SOC2, HIPAA, CIS controls as concrete constraints
   - Each framework's requirements become executable checks
   - RIZQ-specific policies layered on top

3. SMART ANCHOR SYSTEM
   - Risk-weighted autonomy budget (safe ops free, risky ops cost more)
   - Dynamic trust score that builds with clean ops, depletes with warnings
   - Drift detection across operation history (escalating access, speed, repetition)
   - Continuous self-validation after each operation
   - Tunable parameters for fine-tuning autonomy vs oversight

4. INTEGRATION
   - Pre-check (before operation): Can we proceed?
   - Post-record (after operation): Adjust trust, check for drift
   - Single EquilibriumGuard class wraps both systems
   - Audit trail built-in (operation history)

Key insight: "can't vs shouldn't"
- Traditional: Check policy → warn/log if violated
- Equilibrium: Validate constraints → invalid operations physically cannot proceed

Key improvement: Smart autonomy
- Old: Count to 5 and stop
- New: Risk-weighted budget + trust score + drift detection
- Safe operations can run indefinitely
- Risky operations deplete budget and require checkpoints
- Sustained good behavior builds trust → more autonomy
"""
