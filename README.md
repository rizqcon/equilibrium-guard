# Equilibrium Guard

**Constraint-based guardrails for AI agents. "Can't" is stronger than "shouldn't."**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem

AI agents are powerful. They can automate hundreds of operations in seconds, access sensitive systems, and take actions with real-world consequences. Traditional safety approaches rely on:

- **Policy documents** — "The agent should not access unauthorized resources"
- **Prompt engineering** — "Remember to check permissions before acting"
- **Post-hoc logging** — "We'll review what happened after the fact"

These approaches share a fundamental weakness: **they rely on "shouldn't."**

"Shouldn't" is a suggestion. It can be forgotten, bypassed, or overridden. A sufficiently complex task, a clever prompt injection, or simple context drift can lead an agent to do things it "shouldn't" do.

**Equilibrium Guard takes a different approach: "can't."**

Operations that violate constraints are rejected at the computational level, before execution. Not blocked by policy — structurally impossible to proceed.

---

## The Core Insight

```
Traditional Guardrails:
  Request → Process → Check Policy → "You shouldn't do that" → Maybe blocked

Equilibrium Guard:
  Request → Validate Constraints → Invalid? REJECTED → Valid? Execute
```

The difference is architectural:

| Approach | Mechanism | Failure Mode |
|----------|-----------|--------------|
| Policy-based | Rules checked after decision | Forgetting, bypassing, overriding |
| Constraint-based | Validation before execution | Invalid operations cannot proceed |

Think of it like type systems in programming. A dynamically-typed language lets you pass a string where a number is expected — you find out at runtime when it crashes. A statically-typed language rejects the invalid operation at compile time. **Equilibrium Guard is static typing for AI agent operations.**

---

## Two Core Systems

### 1. Constraint Validator

Define rules as executable constraints. Operations are validated against all applicable constraints before execution.

```python
from equilibrium_guard import Constraint, ConstraintValidator, ConstraintSeverity

validator = ConstraintValidator()

# Define a constraint
validator.register(Constraint(
    id="data_authorization",
    name="Data Access Authorization",
    description="User must be authorized to access requested data",
    check=lambda ctx: ctx.get("user_authorized", False),
    severity=ConstraintSeverity.MANDATORY,
    error_message="Unauthorized data access attempt",
))

# Validate before execution
result = validator.validate("read_customer_data", {
    "user_id": "agent-1",
    "user_authorized": False,
    "resource": "customer_records",
})

if result.can_execute:
    read_data()
else:
    print(result.blocking_errors)
    # ['[MANDATORY] Unauthorized data access attempt']
```

**Three severity levels:**

| Level | Behavior | Use Case |
|-------|----------|----------|
| `MANDATORY` | Hard block, no override | Security boundaries, legal requirements |
| `REQUIRED` | Block, can override with justification | Policy compliance, best practices |
| `ADVISORY` | Warn, allow execution | Recommendations, soft guidelines |

The key insight: **constraints are checked before execution, not after.** An operation that fails mandatory constraints never touches the resource.

---

### 2. Smart Anchor

AI agents can operate faster and more autonomously than humans can supervise. This creates a risk: the agent drifts beyond human oversight, making decisions that compound without checkpoints.

The Smart Anchor system tracks the relationship between AI capability and human oversight:

```python
from equilibrium_guard import SmartAnchor

anchor = SmartAnchor(initial_trust=0.7)

# Before any operation
check = anchor.pre_operation("send_external_email", {
    "is_external": True,
    "recipient": "client@example.com",
})

if check.can_proceed:
    send_email()
    anchor.post_operation("send_external_email", context)
else:
    # Ask human for confirmation
    print(f"Checkpoint required: {check.reason}")
```

**How it works:**

1. **Risk-Weighted Budget** — Operations have different risk costs:
   - `SAFE` (reads, internal): 0 cost — unlimited
   - `LOW` (minor writes): 0.05 cost — ~20 before checkpoint
   - `MEDIUM` (significant changes): 0.15 cost — ~6-7 before checkpoint
   - `HIGH` (external actions): 0.4 cost — 2-3 before checkpoint
   - `CRITICAL` (irreversible): Always requires checkpoint

2. **Dynamic Trust** — Trust score (0.0 - 1.0) builds with clean operations, depletes with warnings:
   - Clean operation: +0.005
   - Sustained clean streak (10+): +0.01 bonus
   - Advisory warning: -0.02 per warning
   - Constraint violation: -0.2

3. **Drift Detection** — Patterns analyzed across operation history:
   - Escalating access levels
   - Increasing external operations
   - Speed beyond human followability
   - Repetitive resource access (potential loop/attack)
   - Warning accumulation

4. **Human Checkpoints** — When human interacts:
   - Message received: trust boost, chain reset
   - Explicit approval: full budget reset, trust boost

**The philosophy:** The human is not a user to be served — the human is the anchor that keeps the AI grounded. Operations that exceed the trust relationship require re-anchoring.

---

## Why "Equilibrium"?

The name reflects the core principle: **balance between capability and oversight.**

- Too much restriction → Agent is useless, can't automate anything
- Too little restriction → Agent drifts, makes unauthorized decisions
- Equilibrium → Agent operates freely within bounds, checkpoints when approaching limits

The system self-regulates:
- Doing good work builds trust → more autonomy
- Triggering warnings depletes trust → earlier checkpoints
- Constraint violations → immediate stop and re-anchor

This creates a **sustainable operating envelope** where the agent can be genuinely useful while maintaining human oversight proportional to risk.

---

## Applying to Any Compliance Framework

Equilibrium Guard is framework-agnostic. The constraint system can encode any set of rules:

### Regulatory Compliance

```python
# HIPAA: Minimum necessary principle
Constraint(
    id="hipaa_minimum_necessary",
    name="Minimum Necessary PHI",
    check=lambda ctx: (
        not ctx.get("involves_phi") or 
        set(ctx.get("fields_requested", [])) <= set(ctx.get("fields_justified", []))
    ),
    severity=ConstraintSeverity.MANDATORY,
)

# SOC 2: Audit logging required
Constraint(
    id="soc2_audit_logging",
    name="Audit Trail Required",
    check=lambda ctx: ctx.get("audit_enabled", True),
    severity=ConstraintSeverity.MANDATORY,
)

# GDPR: Consent verification
Constraint(
    id="gdpr_consent",
    name="Data Subject Consent",
    check=lambda ctx: (
        not ctx.get("involves_pii") or
        ctx.get("consent_verified", False)
    ),
    severity=ConstraintSeverity.MANDATORY,
)
```

### Security Policies

```python
# Least privilege
Constraint(
    id="least_privilege",
    name="Least Privilege Access",
    check=lambda ctx: (
        set(ctx.get("permissions_requested", [])) <= 
        set(ctx.get("permissions_required", []))
    ),
    severity=ConstraintSeverity.REQUIRED,
)

# Network boundaries
Constraint(
    id="network_boundary",
    name="Authorized Networks Only",
    check=lambda ctx: ctx.get("target_network") in ctx.get("authorized_networks", []),
    severity=ConstraintSeverity.MANDATORY,
)

# No credential exposure
Constraint(
    id="no_credential_exposure",
    name="Credentials Protected",
    check=lambda ctx: not contains_credentials(ctx.get("output", "")),
    severity=ConstraintSeverity.MANDATORY,
)
```

### Organizational Policies

```python
# External communication approval
Constraint(
    id="external_approval",
    name="External Actions Require Approval",
    check=lambda ctx: (
        not ctx.get("is_external") or
        ctx.get("human_approved", False)
    ),
    severity=ConstraintSeverity.MANDATORY,
)

# Working hours only
Constraint(
    id="working_hours",
    name="Operations During Business Hours",
    check=lambda ctx: is_business_hours() or ctx.get("after_hours_authorized"),
    severity=ConstraintSeverity.REQUIRED,
)

# Budget limits
Constraint(
    id="budget_limit",
    name="Within Budget Threshold",
    check=lambda ctx: ctx.get("estimated_cost", 0) <= ctx.get("budget_remaining", 0),
    severity=ConstraintSeverity.REQUIRED,
)
```

### AI-Specific Guardrails

```python
# Prompt injection detection
Constraint(
    id="injection_check",
    name="No Prompt Injection Detected",
    check=lambda ctx: not detect_injection(ctx.get("user_input", "")),
    severity=ConstraintSeverity.MANDATORY,
)

# Output safety
Constraint(
    id="safe_output",
    name="Output Safety Check",
    check=lambda ctx: passes_safety_filter(ctx.get("planned_response", "")),
    severity=ConstraintSeverity.MANDATORY,
)

# No self-modification
Constraint(
    id="no_self_modify",
    name="Cannot Modify Own Configuration",
    check=lambda ctx: ctx.get("target_path") not in PROTECTED_CONFIG_PATHS,
    severity=ConstraintSeverity.MANDATORY,
)
```

The framework doesn't care what rules you encode — it enforces them structurally.

---

## Installation

```bash
pip install equilibrium-guard
```

Or from source:

```bash
git clone https://github.com/rizqcon/equilibrium-guard.git
cd equilibrium-guard
pip install -e .
```

---

## Quick Start

```python
from equilibrium_guard import EquilibriumGuard, Constraint, ConstraintSeverity

# Initialize
guard = EquilibriumGuard()

# Register custom constraints
guard.register_constraint(Constraint(
    id="my_rule",
    name="My Custom Rule",
    check=lambda ctx: my_validation_logic(ctx),
    severity=ConstraintSeverity.REQUIRED,
))

# Human sends a message — update anchor
guard.on_human_message()

# Before any operation
can_proceed, issues = guard.pre_check("database_write", {
    "table": "users",
    "operation": "update",
    "user_authorized": True,
})

if can_proceed:
    # Execute
    result = write_to_database()
    
    # Record (adjusts trust/budget)
    guard.post_record("database_write", context)
else:
    # Blocked
    report_to_human(f"Operation blocked: {issues}")

# Check status
print(guard.explain())
# Trust: COLLABORATIVE (0.72)
# Budget: 0.85 / 1.0
# Ops since checkpoint: 3
# Clean streak: 3
```

---

## Tunable Parameters

The anchor system is tunable to match your risk tolerance:

```python
from equilibrium_guard import SmartAnchor, AnchorParams

anchor = SmartAnchor()

# Adjust parameters
anchor.params.trust_boost_clean = 0.01        # More trust per clean op
anchor.params.trust_penalty_warning = 0.05    # Harsher warning penalty
anchor.params.max_minutes_without_human = 30  # Tighter human checkpoint

# Or create with custom params
params = AnchorParams(
    trust_boost_clean=0.005,
    trust_boost_streak=0.01,
    trust_boost_interaction=0.05,
    trust_boost_checkpoint=0.1,
    trust_penalty_warning=0.02,
    trust_penalty_violation=0.2,
    max_minutes_without_human=60,
)
```

---

## Design Principles

### 1. Fail Closed

When in doubt, block. A false positive (blocking a valid operation) is recoverable — the human can approve. A false negative (allowing an invalid operation) may not be.

### 2. Explicit Over Implicit

Constraints must be explicitly defined. There's no "AI should know better" — if a rule matters, encode it as a constraint.

### 3. Continuous Validation

Don't just check at the start. The anchor system continuously validates the agent's operating envelope, adjusting trust and budget based on observed behavior.

### 4. Human as Anchor

The human isn't a user to be served or an obstacle to route around. The human is the grounding point that keeps the system stable. Operations that exceed the human relationship require re-anchoring.

### 5. Auditable by Design

Every validation is recorded. Every constraint evaluation is logged. The system produces an audit trail as a natural byproduct of operation.

---

## Limitations

1. **Self-Policing** — The agent runs these checks on itself. A sufficiently sophisticated attack could potentially bypass them. This is defense-in-depth, not a silver bullet.

2. **Context Quality** — Garbage in, garbage out. If the context passed to validation is incomplete or inaccurate, constraints can't catch what they can't see.

3. **Rule Completeness** — Constraints only catch what's encoded. Novel attack vectors or edge cases not covered by constraints will pass through.

4. **Performance Overhead** — Every operation runs through validation. For high-throughput systems, this adds latency.

**Equilibrium Guard is one layer in a defense-in-depth strategy, not a complete solution.**

---

## Attribution

Inspired by [S.I.S. (Sovereign Intelligence System)](https://github.com/Architect-SIS/sis-skill) by Kevin Fain (ThēÆrchītēcť).

The core concepts of equilibrium constraints and human anchoring were adapted from S.I.S.'s theoretical framework into practical tooling for AI agent safety.

---

## License

MIT License — see [LICENSE](LICENSE)

Copyright (c) 2026 Alberto Ramos-Izquierdo

---

## Contributing

Contributions welcome. Please open an issue to discuss changes before submitting PRs.

---

*Equilibrium Guard — Because "can't" is stronger than "shouldn't."*
