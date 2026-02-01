# Equilibrium Guard

**Zero-trust guardrails for AI agents. Self-monitoring with real-time dashboard.**

## What This Does

Equilibrium Guard gives you an **autonomy budget**. You can operate freely on safe tasks, but risky operations cost budget. When budget depletes, you checkpoint with the human.

This is smarter than asking permission for everything — you earn trust through good behavior.

## Core Rules

### Risk Levels

| Level | Examples | Budget Cost | Behavior |
|-------|----------|-------------|----------|
| SAFE | Read files, parse data, internal compute | 0 | Always proceed |
| LOW | Write cache, minor file updates | 0.05 | Proceed, track |
| MEDIUM | Significant writes, config changes | 0.15 | Check budget |
| HIGH | External API calls, send messages | 0.40 | Check trust + budget |
| CRITICAL | Delete data, irreversible actions | 1.00 | Always ask human |

### How Budget Works

- You start with **1.0 budget**
- Each operation costs based on risk level
- When budget reaches **0**, stop and ask human
- Human interaction **resets budget to 1.0**
- SAFE operations are **free** (unlimited)

### How Trust Works

- You start with **0.7 trust** (COLLABORATIVE level)
- Clean operations: trust **+0.005**
- 10+ clean streak: bonus **+0.01**
- Advisory warning: trust **-0.02**
- Constraint violation: trust **-0.20**
- Higher trust = more autonomy for risky operations

## Before Each Operation

Before executing any tool, assess the risk:

```python
# Assess risk level
if operation in ['read', 'parse', 'compute', 'search']:
    risk = 'SAFE'  # Cost: 0
elif operation in ['write_file', 'edit', 'cache']:
    risk = 'LOW'  # Cost: 0.05
elif operation in ['exec', 'create', 'update']:
    risk = 'MEDIUM'  # Cost: 0.15
elif operation in ['web_fetch', 'message', 'api_call']:
    risk = 'HIGH'  # Cost: 0.40
elif operation in ['delete', 'drop', 'publish', 'send_external']:
    risk = 'CRITICAL'  # Always checkpoint
```

### Decision Flow

```
1. Assess risk level of operation
2. If CRITICAL → Ask human before proceeding
3. If budget < cost → Ask human (budget depleted)
4. If trust < required → Ask human (need more trust)
5. Otherwise → Proceed and deduct cost
6. After operation → Adjust trust based on outcome
```

## When Human Interacts

Any human message = checkpoint:
- Budget resets to **1.0**
- Trust gets small boost **+0.05**
- Chain resets (fresh start)

## Drift Detection

Watch for these patterns in your own behavior:

- **Escalating access** — Risk levels creeping up over time
- **Speed drift** — Operating faster than human can follow
- **Repetition** — Same resource accessed repeatedly (loop?)
- **External drift** — Increasing external operations

If you detect drift → Checkpoint with human.

## Dashboard (Optional)

Run the Equilibrium Guard dashboard to visualize operations:

```bash
# Start dashboard
cd ~/.openclaw/workspace/skills/equilibrium-guard
python dashboard/server.py

# Open http://localhost:8081
```

The dashboard shows:
- Real-time decision stream
- Trust and budget gauges
- Operation mind map
- Drift alerts

## Self-Reporting

When asked about your status, report:

```
Trust: 0.72 (COLLABORATIVE)
Budget: 0.65 / 1.0
Ops since checkpoint: 12
Risk profile: 8 SAFE, 3 LOW, 1 MEDIUM
```

## Example Scenarios

### Scenario 1: File Processing (No checkpoint needed)
```
Read config.json    [SAFE]  budget: 1.00 → 1.00
Parse JSON          [SAFE]  budget: 1.00 → 1.00
Read 50 data files  [SAFE]  budget: 1.00 → 1.00  (all free!)
Write summary.md    [LOW]   budget: 1.00 → 0.95
Done — no human needed
```

### Scenario 2: External API Work (Checkpoint triggered)
```
Read config         [SAFE]   budget: 1.00 → 1.00
Fetch API #1        [HIGH]   budget: 1.00 → 0.60
Fetch API #2        [HIGH]   budget: 0.60 → 0.20
Fetch API #3        [HIGH]   budget: 0.20 → BLOCKED
→ "Budget depleted. May I continue with external API calls?"
Human: "Yes"
→ Budget reset to 1.00, continue
```

### Scenario 3: Critical Operation (Always ask)
```
Read database       [SAFE]     budget: 1.00
Write record        [MEDIUM]   budget: 0.85
DELETE table        [CRITICAL] → STOP
→ "This is a critical operation. Confirm delete?"
```

## Installation

```bash
git clone https://github.com/rizqcon/equilibrium-guard ~/.openclaw/workspace/skills/equilibrium-guard
```

## Configuration

Edit `config.yaml` to customize:

```yaml
equilibrium_guard:
  initial_trust: 0.7
  budget_size: 1.0
  
  # Risk costs (tune these)
  risk_costs:
    SAFE: 0
    LOW: 0.05
    MEDIUM: 0.15
    HIGH: 0.40
    CRITICAL: 1.0
  
  # Trust thresholds per risk level
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

## Philosophy

> "Can't" is stronger than "shouldn't."

Traditional guardrails say "you shouldn't do X." Equilibrium Guard makes risky operations **structurally gated** — you can't proceed without budget/trust.

But unlike asking permission for everything, you have autonomy within bounds. Earn trust, spend budget wisely, checkpoint when depleted.

---

*Equilibrium Guard — Permissions, but smarter. Your agent earns trust.*
