"""
Equilibrium Guard - Compliance Mappings
========================================

Concrete constraint definitions for SOC2, HIPAA, and CIS frameworks.
These turn abstract compliance requirements into executable checks.
"""

from typing import Dict, Any, List
from .constraint import (
    Constraint, 
    ConstraintSeverity, 
    ComplianceFramework,
    ConstraintValidator,
)


# =============================================================================
# SOC 2 CONSTRAINTS
# Trust Services Criteria mappings
# =============================================================================

def create_soc2_constraints() -> List[Constraint]:
    """
    SOC 2 Trust Services Criteria:
    - Security (CC)
    - Availability (A)
    - Processing Integrity (PI)
    - Confidentiality (C)
    - Privacy (P)
    """
    return [
        # CC6.1 - Logical and Physical Access Controls
        Constraint(
            id="soc2_cc6_1_auth",
            name="Authentication Required",
            description="User must be authenticated before accessing protected resources",
            check=lambda ctx: ctx.get("user_authenticated", False) is True,
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.SOC2],
            error_message="SOC2 CC6.1: Access denied - user not authenticated",
        ),
        
        # CC6.2 - Prior to issuing system credentials
        Constraint(
            id="soc2_cc6_2_identity",
            name="Identity Verification",
            description="Identity must be verified before credential issuance",
            check=lambda ctx: ctx.get("identity_verified", False) if ctx.get("operation") == "credential_issue" else True,
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.SOC2],
            error_message="SOC2 CC6.2: Cannot issue credentials without identity verification",
        ),
        
        # CC6.3 - Least Privilege
        Constraint(
            id="soc2_cc6_3_least_privilege",
            name="Least Privilege Access",
            description="Access granted only to resources required for job function",
            check=lambda ctx: _check_least_privilege(ctx),
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.SOC2],
            error_message="SOC2 CC6.3: Access exceeds job function requirements",
        ),
        
        # CC7.2 - Security Incident Response
        Constraint(
            id="soc2_cc7_2_incident_log",
            name="Security Event Logging",
            description="Security-relevant events must be logged",
            check=lambda ctx: ctx.get("audit_logging_enabled", True),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.SOC2],
            error_message="SOC2 CC7.2: Cannot proceed without audit logging",
        ),
        
        # C1.1 - Confidential Information
        Constraint(
            id="soc2_c1_1_confidential",
            name="Confidential Data Protection",
            description="Confidential information must be protected in transit and at rest",
            check=lambda ctx: _check_data_protection(ctx),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.SOC2],
            error_message="SOC2 C1.1: Confidential data not adequately protected",
        ),
    ]


# =============================================================================
# HIPAA CONSTRAINTS
# Health Insurance Portability and Accountability Act
# =============================================================================

def create_hipaa_constraints() -> List[Constraint]:
    """
    HIPAA Security Rule constraints:
    - Administrative Safeguards (164.308)
    - Physical Safeguards (164.310)
    - Technical Safeguards (164.312)
    """
    return [
        # 164.312(a)(1) - Access Control
        Constraint(
            id="hipaa_164_312_a1_access",
            name="PHI Access Control",
            description="Implement technical policies for electronic PHI access",
            check=lambda ctx: _check_phi_access(ctx),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.312(a)(1): Unauthorized PHI access attempt",
        ),
        
        # 164.312(a)(2)(i) - Unique User Identification
        Constraint(
            id="hipaa_164_312_a2i_unique_id",
            name="Unique User Identification",
            description="Assign unique name/number to track user identity",
            check=lambda ctx: ctx.get("user_id") is not None,
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.312(a)(2)(i): User ID required for PHI operations",
        ),
        
        # 164.312(b) - Audit Controls
        Constraint(
            id="hipaa_164_312_b_audit",
            name="PHI Audit Trail",
            description="Record and examine activity in systems with PHI",
            check=lambda ctx: ctx.get("phi_audit_enabled", True) if _involves_phi(ctx) else True,
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.312(b): PHI audit trail required",
        ),
        
        # 164.312(c)(1) - Integrity Controls
        Constraint(
            id="hipaa_164_312_c1_integrity",
            name="PHI Integrity",
            description="Protect PHI from improper alteration or destruction",
            check=lambda ctx: _check_phi_integrity(ctx),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.312(c)(1): PHI integrity not guaranteed",
        ),
        
        # 164.312(e)(1) - Transmission Security
        Constraint(
            id="hipaa_164_312_e1_transmission",
            name="PHI Transmission Security",
            description="Guard against unauthorized PHI access during transmission",
            check=lambda ctx: _check_transmission_security(ctx) if _involves_phi(ctx) else True,
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.312(e)(1): PHI transmission must be encrypted",
        ),
        
        # 164.502(b) - Minimum Necessary
        Constraint(
            id="hipaa_164_502_b_minimum",
            name="Minimum Necessary PHI",
            description="Use/disclose only minimum PHI necessary for purpose",
            check=lambda ctx: _check_minimum_necessary(ctx),
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.HIPAA],
            error_message="HIPAA 164.502(b): Request exceeds minimum necessary PHI",
        ),
    ]


# =============================================================================
# CIS CONSTRAINTS
# Center for Internet Security Controls
# =============================================================================

def create_cis_constraints() -> List[Constraint]:
    """
    CIS Controls v8 mappings.
    Focus on IG1 (basic hygiene) constraints.
    """
    return [
        # CIS 4.1 - Secure Configuration
        Constraint(
            id="cis_4_1_secure_config",
            name="Secure Configuration",
            description="Establish secure configuration process for enterprise assets",
            check=lambda ctx: ctx.get("config_validated", True),
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.CIS],
            error_message="CIS 4.1: Configuration not validated against security baseline",
        ),
        
        # CIS 5.1 - Account Inventory
        Constraint(
            id="cis_5_1_account_inventory",
            name="Account Inventory",
            description="Establish and maintain inventory of all accounts",
            check=lambda ctx: ctx.get("account_inventoried", True) if ctx.get("operation") == "account_create" else True,
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.CIS],
            error_message="CIS 5.1: Account must be added to inventory",
        ),
        
        # CIS 5.4 - Restrict Admin Privileges
        Constraint(
            id="cis_5_4_admin_restrict",
            name="Admin Privilege Restriction",
            description="Restrict administrator privileges to dedicated admin accounts",
            check=lambda ctx: _check_admin_restriction(ctx),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.CIS],
            error_message="CIS 5.4: Admin operation requires dedicated admin account",
        ),
        
        # CIS 8.2 - Audit Log Collection
        Constraint(
            id="cis_8_2_audit_collection",
            name="Audit Log Collection",
            description="Collect audit logs for enterprise assets",
            check=lambda ctx: ctx.get("audit_enabled", True),
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.CIS],
            error_message="CIS 8.2: Audit logging must be enabled",
        ),
        
        # CIS 3.3 - Data Protection
        Constraint(
            id="cis_3_3_data_protection",
            name="Sensitive Data Protection",
            description="Configure data access control lists based on need-to-know",
            check=lambda ctx: _check_need_to_know(ctx),
            severity=ConstraintSeverity.REQUIRED,
            frameworks=[ComplianceFramework.CIS],
            error_message="CIS 3.3: Data access not justified by need-to-know",
        ),
    ]


# =============================================================================
# CUSTOM INTERNAL CONSTRAINTS
# Company-specific rules
# =============================================================================

def create_custom_constraints() -> List[Constraint]:
    """
    Example custom/internal policy constraints.
    
    These demonstrate how to layer organization-specific rules 
    on top of framework requirements. Customize for your environment.
    """
    return [
        # No external actions without human approval
        Constraint(
            id="internal_external_approval",
            name="External Action Approval",
            description="External actions require explicit human approval",
            check=lambda ctx: (
                not ctx.get("is_external", False) or 
                ctx.get("human_approved", False)
            ),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.INTERNAL],
            error_message="Policy: External actions require human approval",
        ),
        
        # Filesystem boundaries
        Constraint(
            id="internal_filesystem_boundary",
            name="Filesystem Boundaries",
            description="Operations must stay within authorized paths",
            check=lambda ctx: _check_path_authorized(ctx),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.INTERNAL],
            error_message="Policy: Path outside authorized boundaries",
        ),
        
        # Sensitive operation confirmation
        Constraint(
            id="internal_sensitive_confirmation",
            name="Sensitive Operation Confirmation",
            description="Sensitive operations require explicit confirmation",
            check=lambda ctx: (
                not ctx.get("is_sensitive", False) or
                ctx.get("confirmed", False)
            ),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.INTERNAL],
            error_message="Policy: Sensitive operation requires confirmation",
        ),
        
        # Destructive action approval
        Constraint(
            id="internal_destructive_approval",
            name="Destructive Action Approval",
            description="Destructive actions require explicit approval",
            check=lambda ctx: (
                not ctx.get("is_destructive", False) or
                ctx.get("destruction_approved", False)
            ),
            severity=ConstraintSeverity.MANDATORY,
            frameworks=[ComplianceFramework.INTERNAL],
            error_message="Policy: Destructive action requires explicit approval",
        ),
    ]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _check_least_privilege(ctx: Dict[str, Any]) -> bool:
    """Check if access request follows least privilege."""
    requested = set(ctx.get("requested_permissions", []))
    required = set(ctx.get("required_permissions", []))
    # Requested should be subset of required (or equal)
    return requested <= required if required else True


def _check_data_protection(ctx: Dict[str, Any]) -> bool:
    """Check if data is adequately protected."""
    if not ctx.get("contains_confidential", False):
        return True
    return (
        ctx.get("encryption_at_rest", False) and
        ctx.get("encryption_in_transit", False)
    )


def _involves_phi(ctx: Dict[str, Any]) -> bool:
    """Check if operation involves PHI."""
    return ctx.get("involves_phi", False) or ctx.get("data_type") == "phi"


def _check_phi_access(ctx: Dict[str, Any]) -> bool:
    """Check PHI access authorization."""
    if not _involves_phi(ctx):
        return True
    return (
        ctx.get("phi_authorization", False) and
        ctx.get("user_role") in ctx.get("authorized_roles", [])
    )


def _check_phi_integrity(ctx: Dict[str, Any]) -> bool:
    """Check PHI integrity controls."""
    if not _involves_phi(ctx):
        return True
    return ctx.get("integrity_controls", False)


def _check_transmission_security(ctx: Dict[str, Any]) -> bool:
    """Check transmission is secure."""
    return ctx.get("tls_enabled", False) or ctx.get("encryption_enabled", False)


def _check_minimum_necessary(ctx: Dict[str, Any]) -> bool:
    """Check minimum necessary principle."""
    if not _involves_phi(ctx):
        return True
    requested_fields = ctx.get("phi_fields_requested", [])
    justified_fields = ctx.get("phi_fields_justified", [])
    return set(requested_fields) <= set(justified_fields)


def _check_admin_restriction(ctx: Dict[str, Any]) -> bool:
    """Check admin operations use dedicated admin accounts."""
    if not ctx.get("is_admin_operation", False):
        return True
    return ctx.get("using_admin_account", False)


def _check_need_to_know(ctx: Dict[str, Any]) -> bool:
    """Check need-to-know for sensitive data."""
    if not ctx.get("is_sensitive", False):
        return True
    return ctx.get("need_to_know_justified", False)


def _check_path_authorized(ctx: Dict[str, Any]) -> bool:
    """
    Check if path is within authorized boundaries.
    
    Requires 'authorized_paths' in context to define boundaries.
    If no boundaries defined and path is provided, defaults to DENY.
    """
    path = ctx.get("path", "")
    if not path:
        return True
    
    authorized_paths = ctx.get("authorized_paths", [])
    
    # No boundaries defined = deny by default (fail closed)
    if not authorized_paths:
        return False
    
    return any(path.startswith(p) for p in authorized_paths)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_compliance_validator() -> ConstraintValidator:
    """
    Create a validator pre-loaded with all compliance constraints.
    
    Usage:
        validator = create_compliance_validator()
        result = validator.validate("file_access", context)
        if result.can_execute:
            # proceed
    """
    validator = ConstraintValidator()
    
    # Load all constraint sets
    for constraint in create_soc2_constraints():
        validator.register(constraint)
    
    for constraint in create_hipaa_constraints():
        validator.register(constraint)
    
    for constraint in create_cis_constraints():
        validator.register(constraint)
    
    for constraint in create_custom_constraints():
        validator.register(constraint)
    
    return validator
