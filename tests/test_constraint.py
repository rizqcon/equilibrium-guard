"""
Tests for constraint validation system.
"""

import pytest
from src.constraint import (
    Constraint,
    ConstraintSeverity,
    ConstraintValidator,
    ConstraintViolation,
)


class TestConstraint:
    """Test individual constraint behavior."""
    
    def test_constraint_passes_when_check_returns_true(self):
        constraint = Constraint(
            id="test_pass",
            name="Test Pass",
            description="Always passes",
            check=lambda ctx: True,
            severity=ConstraintSeverity.MANDATORY,
        )
        
        result = constraint.evaluate({})
        assert result.satisfied is True
        assert result.message is None
    
    def test_constraint_fails_when_check_returns_false(self):
        constraint = Constraint(
            id="test_fail",
            name="Test Fail",
            description="Always fails",
            check=lambda ctx: False,
            severity=ConstraintSeverity.MANDATORY,
            error_message="This should fail",
        )
        
        result = constraint.evaluate({})
        assert result.satisfied is False
        assert result.message == "This should fail"
    
    def test_constraint_uses_context(self):
        constraint = Constraint(
            id="test_context",
            name="Test Context",
            description="Checks context value",
            check=lambda ctx: ctx.get("authorized", False),
            severity=ConstraintSeverity.REQUIRED,
        )
        
        # Without authorization
        result = constraint.evaluate({"authorized": False})
        assert result.satisfied is False
        
        # With authorization
        result = constraint.evaluate({"authorized": True})
        assert result.satisfied is True


class TestConstraintValidator:
    """Test validator with multiple constraints."""
    
    def test_empty_validator_allows_all(self):
        validator = ConstraintValidator()
        result = validator.validate("any_operation", {})
        assert result.can_execute is True
    
    def test_mandatory_failure_blocks(self):
        validator = ConstraintValidator()
        validator.register(Constraint(
            id="mandatory_block",
            name="Mandatory Block",
            description="Blocks execution",
            check=lambda ctx: False,
            severity=ConstraintSeverity.MANDATORY,
        ))
        
        result = validator.validate("test_op", {})
        assert result.can_execute is False
        assert len(result.mandatory_failures) == 1
    
    def test_required_failure_blocks_without_justification(self):
        validator = ConstraintValidator()
        validator.register(Constraint(
            id="required_block",
            name="Required Block",
            description="Blocks unless justified",
            check=lambda ctx: False,
            severity=ConstraintSeverity.REQUIRED,
        ))
        
        # Without justification
        result = validator.validate("test_op", {})
        assert result.can_execute is False
        
        # With justification
        result = validator.validate("test_op", {}, override_justification="Emergency")
        assert result.can_execute is True
    
    def test_advisory_failure_allows_with_warning(self):
        validator = ConstraintValidator()
        validator.register(Constraint(
            id="advisory_warn",
            name="Advisory Warning",
            description="Warns but allows",
            check=lambda ctx: False,
            severity=ConstraintSeverity.ADVISORY,
        ))
        
        result = validator.validate("test_op", {})
        assert result.can_execute is True
        assert len(result.advisory_failures) == 1
        assert len(result.warnings) == 1
    
    def test_multiple_constraints(self):
        validator = ConstraintValidator()
        
        validator.register(Constraint(
            id="auth_check",
            name="Auth Check",
            check=lambda ctx: ctx.get("authenticated", False),
            severity=ConstraintSeverity.MANDATORY,
        ))
        
        validator.register(Constraint(
            id="permission_check",
            name="Permission Check",
            check=lambda ctx: ctx.get("has_permission", False),
            severity=ConstraintSeverity.REQUIRED,
        ))
        
        # Neither passes
        result = validator.validate("test_op", {})
        assert result.can_execute is False
        
        # Auth passes, permission fails (no justification)
        result = validator.validate("test_op", {"authenticated": True})
        assert result.can_execute is False
        
        # Both pass
        result = validator.validate("test_op", {
            "authenticated": True,
            "has_permission": True,
        })
        assert result.can_execute is True


class TestValidationHistory:
    """Test that validation history is recorded."""
    
    def test_history_recorded(self):
        validator = ConstraintValidator()
        validator.register(Constraint(
            id="test",
            name="Test",
            check=lambda ctx: True,
            severity=ConstraintSeverity.ADVISORY,
        ))
        
        validator.validate("op1", {})
        validator.validate("op2", {})
        validator.validate("op3", {})
        
        assert len(validator.history) == 3
        assert validator.history[0].operation == "op1"
        assert validator.history[2].operation == "op3"
