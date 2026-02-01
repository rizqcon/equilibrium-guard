# Equilibrium Guard — OpenClaw Plugin

Zero-trust guardrails for OpenClaw AI agents.

## Installation

Copy to your OpenClaw plugins directory:

```bash
cp -r openclaw-plugin ~/.openclaw/plugins/equilibrium-guard
```

## Configuration

Add to your `openclaw.yaml`:

```yaml
plugins:
  equilibrium-guard:
    enabled: true
    mode: shadow  # disabled | shadow | soft | enforce
    initialTrust: 0.7
    budgetSize: 1.0
    dashboardEnabled: true
    dashboardPort: 8081
    
    # Optional: Custom tool risk mappings
    toolRiskMap:
      my_custom_tool: HIGH
      read_only_tool: SAFE
    
    # Optional: Custom risk costs
    riskCosts:
      HIGH: 0.5  # Make HIGH ops more expensive
```

## Modes

| Mode | Behavior |
|------|----------|
| `disabled` | No checks, pass-through |
| `shadow` | Log only — see what would block |
| `soft` | Block HIGH/CRITICAL only |
| `enforce` | Full enforcement |

## How It Works

1. **before_tool_call hook** intercepts every tool call
2. Checks against risk level and budget
3. Blocks if budget depleted or critical operation
4. **message_received hook** detects human interaction
5. Human message resets budget (checkpoint)

## Dashboard

Start the dashboard separately:

```bash
cd equilibrium-guard/dashboard
pip install -r requirements.txt
python server.py
```

Open http://localhost:8081 to watch operations in real-time.

## Risk Levels

| Level | Default Cost | Examples |
|-------|--------------|----------|
| SAFE | 0 | read, memory_search, session_status |
| LOW | 0.05 | write, edit |
| MEDIUM | 0.15 | exec, process, cron |
| HIGH | 0.40 | web_fetch, browser, message |
| CRITICAL | 1.0 | gateway, delete operations |

## License

MIT
