# Equilibrium Guard

**Zero-trust guardrails for AI agents. "Can't" is stronger than "shouldn't."**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> ⚠️ **This is a concept proposal and proof-of-concept implementation.**
> 
> Equilibrium Guard is an exploration of what zero-trust security for AI agents *could* look like. The code is functional for demonstration purposes, but this is not production-ready software. We're sharing this to start a conversation about AI agent security patterns and invite collaboration.

<img width="1920" height="1040" alt="image" src="https://github.com/user-attachments/assets/85d713e1-7d12-4de0-9d3c-5bc74b4e6f2b" />

*Proof-of-concept dashboard showing trust score, risk budget, operation mind map, decision storyline, and drift alerts.*

---

## What Is This?

Equilibrium Guard is a **concept proposal** for zero-trust security in AI agents. It explores:

1. **Constraint Validation** — Operations checked against rules *before* execution
2. **Risk-Weighted Autonomy** — Safe operations are free; risky ones cost budget
3. **Dynamic Trust** — Good behavior builds trust; warnings deplete it
4. **Drift Detection** — Catches patterns like escalating access or speed anomalies
5. **Real-Time Dashboard** — Watch your agent's decisions as they happen

Think of it like **ThreatLocker or SentinelOne, but for AI operations.**

### Why Share This?

AI agents are getting more capable and more autonomous. The security tooling hasn't kept up. We built this concept to:

- **Start a conversation** about AI agent security patterns
- **Prototype ideas** that could become real products
- **Invite collaboration** from the community

This is a sketch, not a finished building. If these ideas resonate, let's build something real together.

---

## The Zero-Trust Approach

Traditional AI safety relies on prompts and policies — "the agent *should* do X" or "*shouldn't* do Y." This is fundamentally weak because:

- Prompts can be forgotten, overridden, or injected
- Policy documents aren't enforced computationally
- Post-hoc logging catches problems too late

**Equilibrium Guard enforces "can't" instead of "shouldn't":**

```
Traditional:  Request → Process → Check Policy → "You shouldn't" → Maybe blocked
Zero-Trust:   Request → Validate → Invalid? REJECTED → Valid? Execute
```

Operations that violate constraints are rejected at the computational level, before execution. Not blocked by policy — **structurally impossible to proceed.**

---

## Quick Start

### Installation

```bash
pip install equilibrium-guard
```

Or clone and install:

```bash
git clone https://github.com/rizqcon/equilibrium-guard
cd equilibrium-guard
pip install -e .
```

### Basic Usage

```python
from equilibrium_guard import create_guard

# Initialize with zero-trust defaults
guard = create_guard(mode='enforce')

# Human sends a message — update anchor
guard.on_human_message()

# Before any operation
can_proceed, issues = guard.pre_check("database_write", {
    "table": "users",
    "operation": "update",
})

if can_proceed:
    result = write_to_database()
    guard.post_record("database_write", context)
else:
    report_to_human(f"Blocked: {issues}")
```

---

## Zero-Trust Configuration

The core of Equilibrium Guard is the **risk-weighted autonomy budget**. Every operation has a risk level, and risky operations cost budget.

### Risk Levels

| Level | Cost | Budget Impact | Examples |
|-------|------|---------------|----------|
| **SAFE** | 0 | Unlimited | Read files, parse data, internal compute |
| **LOW** | 0.05 | ~20 ops before checkpoint | Write cache, minor updates |
| **MEDIUM** | 0.15 | ~6-7 ops before checkpoint | Exec commands, config changes |
| **HIGH** | 0.40 | 2-3 ops before checkpoint | API calls, send messages |
| **CRITICAL** | 1.0 | Always checkpoint | Delete data, irreversible actions |

### Trust Levels

Trust builds with clean operations and depletes with warnings:

| Trust Score | Level | Behavior |
|-------------|-------|----------|
| 0.95+ | AUTONOMOUS | Maximum autonomy |
| 0.80+ | HIGH_TRUST | High-risk ops allowed |
| 0.60+ | COLLABORATIVE | Standard operation |
| 0.40+ | CAUTIOUS | Frequent checkpoints |
| 0.20+ | MINIMAL | Most ops require approval |
| <0.20 | DISCONNECTED | Almost everything blocked |

### Trust Dynamics

```python
# Trust increases with good behavior
clean_operation:        +0.005
streak_bonus (10+):     +0.01
human_message:          +0.05
explicit_approval:      +0.10

# Trust decreases with problems
advisory_warning:       -0.02
constraint_violation:   -0.20
```

### Configuration File

```yaml
# config.yaml
equilibrium_guard:
  # Starting values
  initial_trust: 0.7      # COLLABORATIVE level
  budget_size: 1.0        # Full budget
  
  # Mode: disabled | shadow | soft | enforce
  mode: shadow
  
  # Risk costs (tune to your risk tolerance)
  risk_costs:
    SAFE: 0
    LOW: 0.05
    MEDIUM: 0.15
    HIGH: 0.40
    CRITICAL: 1.0
  
  # Minimum trust required per risk level
  trust_required:
    SAFE: 0
    LOW: 0.2
    MEDIUM: 0.4
    HIGH: 0.6
    CRITICAL: 0.8
  
  # Drift detection
  max_minutes_without_human: 60
  speed_threshold_per_minute: 60
```

---

## Enforcement Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `disabled` | No checks | Development/testing |
| `shadow` | Log only, never block | Learning phase — see what *would* block |
| `soft` | Block HIGH/CRITICAL only | Gradual rollout |
| `enforce` | Full enforcement | Production |

**Recommended rollout:**

1. Start in `shadow` mode — observe patterns
2. Move to `soft` — catch high-risk issues
3. Graduate to `enforce` — full zero-trust

---

## Drift Detection

The system watches for behavioral patterns that indicate drift from normal operation:

| Pattern | Trigger | Concern |
|---------|---------|---------|
| **Escalating Access** | Risk levels creeping up | Prompt injection, task drift |
| **Speed Drift** | >60 ops/minute | Faster than human can follow |
| **Repetition** | Same resource 5+ times | Potential loop or attack |
| **External Drift** | Increasing external ops | Expanding attack surface |
| **Warning Accumulation** | 3+ warnings in window | Something's wrong |

When drift is detected → automatic checkpoint with human required.

---

## Real-Time Dashboard

Monitor your agent's operations in real-time:

```bash
cd equilibrium-guard
pip install -r dashboard/requirements.txt
python dashboard/server.py

# Open http://localhost:8081
```

**Dashboard features:**

| Component | Description |
|-----------|-------------|
| **Guard Status** | Mode, trust score, budget with animated gauges |
| **Mode Control** | Switch between disabled/shadow/soft/enforce |
| **Human Checkpoint** | Reset budget from the dashboard |
| **Operation Mind Map** | Visual map of all operations, color-coded by risk |
| **Decision Storyline** | Real-time feed with ✅ (passed), ⚠️ (would block), 🚫 (blocked) |
| **Drift Alerts** | Actionable alerts with Acknowledge/Checkpoint buttons |

The dashboard connects via WebSocket for instant updates — no polling.

---

## Constraint System

Beyond risk budgets, define explicit constraints:

```python
from equilibrium_guard import Constraint, ConstraintSeverity

guard.register_constraint(Constraint(
    id="no_production_writes",
    name="Production Write Protection",
    check=lambda ctx: (
        ctx.get("environment") != "production" or
        ctx.get("human_approved", False)
    ),
    severity=ConstraintSeverity.MANDATORY,
    error_message="Production writes require human approval",
))
```

**Severity levels:**

| Level | Behavior |
|-------|----------|
| `MANDATORY` | Hard block, no override — security boundaries |
| `REQUIRED` | Block, can override with justification |
| `ADVISORY` | Warn but allow — recommendations |

---

## Compliance Mapping

Encode any compliance framework as constraints:

### HIPAA

```python
Constraint(
    id="hipaa_minimum_necessary",
    name="Minimum Necessary PHI",
    check=lambda ctx: (
        not ctx.get("involves_phi") or 
        set(ctx.get("fields_requested", [])) <= set(ctx.get("fields_justified", []))
    ),
    severity=ConstraintSeverity.MANDATORY,
)
```

### SOC 2

```python
Constraint(
    id="soc2_audit_logging",
    name="Audit Trail Required",
    check=lambda ctx: ctx.get("audit_enabled", True),
    severity=ConstraintSeverity.MANDATORY,
)
```

### CIS Controls

```python
Constraint(
    id="cis_least_privilege",
    name="Least Privilege Access",
    check=lambda ctx: (
        set(ctx.get("permissions_requested", [])) <= 
        set(ctx.get("permissions_required", []))
    ),
    severity=ConstraintSeverity.REQUIRED,
)
```

See [compliance_map.py](src/compliance_map.py) for more examples.

---

## OpenClaw Skill

For OpenClaw users, install as a skill:

```bash
git clone https://github.com/rizqcon/equilibrium-guard
cd equilibrium-guard/skill
./install.sh
```

Your agent reads `SKILL.md` and learns to self-monitor. The skill includes:

- Risk assessment rules
- Budget tracking instructions
- Checkpoint protocols
- Dashboard integration

See [skill/SKILL.md](skill/SKILL.md) for the full agent instructions.

---

## Philosophy

### "Can't" vs "Shouldn't"

Traditional guardrails say "you shouldn't do X." Equilibrium Guard makes risky operations **structurally gated** — you can't proceed without budget/trust.

### Earned Autonomy

Unlike permission systems that ask every time, agents start with an autonomy budget. They can work independently on safe tasks, checkpointing only when budget depletes or trust is insufficient.

### Human as Anchor

The human isn't a user to be served — the human is the **anchor** that keeps the AI grounded. Operations that exceed the trust relationship require re-anchoring.

### Defense in Depth

Equilibrium Guard is one layer, not a silver bullet:

- Constraints catch known rules
- Trust/budget catches unknown drift
- Dashboard provides observability
- Human checkpoints provide ultimate override

---

## Current Status

This is a **proof-of-concept**. What exists:

- ✅ Core constraint validator (functional)
- ✅ Smart anchor with trust/budget (functional)
- ✅ Real-time WebSocket dashboard (functional)
- ✅ OpenClaw skill package (functional)
- ⚠️ Integration with actual AI agents (manual/self-policing)
- ❌ Automated enforcement layer (not implemented)
- ❌ Production hardening (not done)
- ❌ Comprehensive test coverage (minimal)

**This is a concept exploration, not production software.**

---

## Limitations

1. **Self-Policing** — The agent runs checks on itself. Sophisticated attacks could potentially bypass.
2. **Context Quality** — Garbage in, garbage out. Validation only sees what you pass.
3. **Rule Completeness** — Only catches what's encoded. Novel vectors may pass.
4. **Performance** — Every operation runs through validation. Adds latency.
5. **Proof-of-Concept** — Not battle-tested. Use for exploration and prototyping.

**Use as part of defense-in-depth, not as a complete solution.**

---

## Attribution

Inspired by [S.I.S. (Sovereign Intelligence System)](https://github.com/Architect-SIS/sis-skill) by Kevin Fain.

The concepts of equilibrium constraints and human anchoring were adapted from S.I.S.'s theoretical framework into practical tooling.

---

## License

MIT License — see [LICENSE](LICENSE)

Copyright (c) 2026 RIZQ Technologies

---

## Contributing

Contributions welcome. Open an issue to discuss before submitting PRs.

---

*Equilibrium Guard — A concept for zero-trust AI agent security. Because "can't" is stronger than "shouldn't."*
