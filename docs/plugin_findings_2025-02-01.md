# 2026-02-01 — Equilibrium Guard OpenClaw Integration Investigation

## Summary

Spent ~2.5 hours attempting to integrate Equilibrium Guard as an OpenClaw plugin. The standalone components (dashboard, Python guard library) work perfectly. The OpenClaw plugin integration hit multiple undocumented barriers.

---

## What Works ✅

### Dashboard Server
- **Location:** `/home/rizqdev/projects/equilibrium-guard/dashboard/`
- **Port:** 8081
- **API Endpoints:**
  - `GET /api/state` — current guard state
  - `GET /api/decisions` — decision history
  - `POST /api/decision` — log a decision event
  - `POST /api/state` — update state
  - WebSocket at `/ws` for real-time updates
- **Status:** Fully functional, tested with manual curl POSTs

### Python Guard Library
- **Location:** `/home/rizqdev/projects/equilibrium-guard/src/`
- Constraint validator, smart anchor, risk weighting all work
- Dashboard bridge sends events via HTTP

### Plugin Discovery
- Plugin is discovered and shows as "loaded" in `openclaw plugins list`
- Plugin's `register()` function is called on gateway startup
- Debug file at `/tmp/equilibrium-guard-debug.log` confirms initialization

---

## What Doesn't Work ❌

### Hook Not Triggering
The `before_tool_call` hook registers but never fires when tools are called.

**Evidence:**
- `api.on("before_tool_call", handler)` accepts the registration
- Handler function is never invoked (no debug log entries)
- Dashboard receives no events from actual tool calls

**Probable cause:** The patched `steerable-agent-loop.js` calls `hookRunner.hasHooks("before_tool_call")` but the typed hooks registered via `api.on()` may not be in the same registry that `hasHooks()` checks, OR there's a timing/initialization issue.

---

## Lessons Learned

### Plugin Discovery Requirements
1. **Symlinks don't work** — `isDirectory()` returns false for symlinks
2. **Must copy plugin directory** to `~/.openclaw/extensions/`
3. **package.json requires:**
   ```json
   {
     "openclaw": {
       "extensions": ["./index.ts"]
     }
   }
   ```
4. **openclaw.plugin.json** provides manifest (id, name, configSchema)

### Hook Registration
- `api.registerHook()` — for manifest-based hooks (not what we need)
- `api.on(hookName, handler)` — for typed runtime hooks (what we used)
- `hasHooks()` checks `registry.typedHooks` array

### The Patch Location
- **File:** `/home/rizqdev/.npm-global/lib/node_modules/openclaw/dist/agents/steerable-agent-loop.js`
- **Patch file:** `/home/rizqdev/.openclaw/patches/before-tool-hook.patch`
- Calls `getGlobalHookRunner().runBeforeToolCall()` before tool execution

### Config Location
- `~/.openclaw/openclaw.json`
- Plugin config under `plugins.entries.{plugin-id}`
- Config schema validated against plugin's `configSchema`

---

## Files Modified/Created

### In equilibrium-guard repo
- `openclaw-plugin/package.json` — added `openclaw.extensions` field
- `openclaw-plugin/index.ts` — changed from `api.registerHook()` to `api.on()`

### In OpenClaw installation
- `dist/agents/steerable-agent-loop.js` — patched to call before_tool_call hook
- `dist/plugins/hook-runner-global.js` — already exists, provides global hook runner

### In ~/.openclaw
- `extensions/equilibrium-guard/` — copied plugin directory
- `openclaw.json` — added plugins.entries.equilibrium-guard

---

## Next Steps

### Option 1: Contribute Upstream (Recommended)
Open a PR to OpenClaw adding official `before_tool_call` hook support:
- Make the patch part of core
- Document hook registration for external plugins
- Add tests

### Option 2: Debug Further
- Add logging inside `steerable-agent-loop.js` at the hook call site
- Check if `hasHooks("before_tool_call")` returns true
- Verify the hook runner has the typed hooks populated

### Option 3: Alternative Architecture
- Build as a proxy layer between OpenClaw and tools
- Or implement as a "meta-tool" that wraps other tool calls
- Less elegant but doesn't require core patches

---

## Repository Status

**GitHub:** github.com/rizqcon/equilibrium-guard

**Commits:**
- `80563a5` - Initial commit: Equilibrium Guard v0.1.0
- `ed69da9` - Add skill package and real-time dashboard

**Branches:** main

---

## Quick Reference Commands

```bash
# Start dashboard
cd /home/rizqdev/projects/equilibrium-guard && ./venv/bin/python dashboard/server.py

# Check dashboard
curl http://localhost:8081/api/state
curl http://localhost:8081/api/decisions

# Test manual event
curl -X POST http://localhost:8081/api/decision \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-02-01T00:00:00Z","operation":"test","risk_level":"MEDIUM","would_block":false,"actually_blocked":false,"reasons":[],"trust_score":0.7,"budget_remaining":1.0}'

# Check plugin status
openclaw plugins list | grep -i equilibrium

# Check if patch is applied
grep "EQUILIBRIUM-GUARD-PATCH" ~/.npm-global/lib/node_modules/openclaw/dist/agents/steerable-agent-loop.js
```

---

*Investigation paused at 12:55 AM. Plugin loads, hook registers, but doesn't fire. Needs deeper debugging or upstream contribution.*
