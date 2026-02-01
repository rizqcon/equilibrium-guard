/**
 * Equilibrium Guard — OpenClaw Plugin
 * =====================================
 * 
 * Zero-trust guardrails for AI agents.
 * Intercepts tool calls via before_tool_call hook.
 * 
 * Install: Copy to ~/.openclaw/plugins/equilibrium-guard/
 * 
 * Config in openclaw.yaml:
 *   plugins:
 *     equilibrium-guard:
 *       enabled: true
 *       mode: shadow  # disabled | shadow | soft | enforce
 *       dashboardEnabled: true
 *       dashboardPort: 8081
 */

import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import * as fs from "fs";

// Risk levels and their default costs
type RiskLevel = "SAFE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

const DEFAULT_RISK_COSTS: Record<RiskLevel, number> = {
  SAFE: 0,
  LOW: 0.05,
  MEDIUM: 0.15,
  HIGH: 0.4,
  CRITICAL: 1.0,
};

// Default tool → risk mappings
const DEFAULT_TOOL_RISK_MAP: Record<string, RiskLevel> = {
  // SAFE - read operations
  read: "SAFE",
  memory_search: "SAFE",
  memory_get: "SAFE",
  web_search: "SAFE",
  agents_list: "SAFE",
  sessions_list: "SAFE",
  sessions_history: "SAFE",
  session_status: "SAFE",
  image: "SAFE",
  
  // LOW - minor writes
  write: "LOW",
  edit: "LOW",
  
  // MEDIUM - significant operations
  exec: "MEDIUM",
  process: "MEDIUM",
  cron: "MEDIUM",
  
  // HIGH - external actions
  web_fetch: "HIGH",
  browser: "HIGH",
  message: "HIGH",
  sessions_send: "HIGH",
  sessions_spawn: "HIGH",
  tts: "HIGH",
  
  // CRITICAL - system/destructive
  gateway: "CRITICAL",
  nodes: "HIGH",
};

interface GuardState {
  trust: number;
  budget: number;
  mode: string;
  opsSinceCheckpoint: number;
  cleanStreak: number;
  lastHumanMs: number;
  history: Array<{
    timestamp: string;
    tool: string;
    risk: RiskLevel;
    blocked: boolean;
  }>;
}

interface PluginConfig {
  mode?: string;
  initialTrust?: number;
  budgetSize?: number;
  dashboardEnabled?: boolean;
  dashboardPort?: number;
  riskCosts?: Partial<Record<RiskLevel, number>>;
  toolRiskMap?: Record<string, RiskLevel>;
}

// Plugin state
let state: GuardState;
let config: PluginConfig;
let dashboardUrl: string;

function initState(cfg: PluginConfig) {
  config = cfg;
  state = {
    trust: cfg.initialTrust ?? 0.7,
    budget: cfg.budgetSize ?? 1.0,
    mode: cfg.mode ?? "shadow",
    opsSinceCheckpoint: 0,
    cleanStreak: 0,
    lastHumanMs: Date.now(),
    history: [],
  };
  dashboardUrl = `http://localhost:${cfg.dashboardPort ?? 8081}`;
}

function getRiskLevel(toolName: string): RiskLevel {
  const customMap = config.toolRiskMap ?? {};
  const merged = { ...DEFAULT_TOOL_RISK_MAP, ...customMap };
  return merged[toolName.toLowerCase()] ?? "MEDIUM";
}

function getRiskCost(risk: RiskLevel): number {
  const customCosts = config.riskCosts ?? {};
  const merged = { ...DEFAULT_RISK_COSTS, ...customCosts };
  return merged[risk] ?? 0.15;
}

function checkOperation(toolName: string): { allow: boolean; reason?: string } {
  const risk = getRiskLevel(toolName);
  const cost = getRiskCost(risk);
  
  // Disabled mode - always allow
  if (state.mode === "disabled") {
    return { allow: true };
  }
  
  // CRITICAL always requires checkpoint (except in shadow mode)
  if (risk === "CRITICAL" && state.mode !== "shadow") {
    return { 
      allow: false, 
      reason: `CRITICAL operation (${toolName}) requires human confirmation` 
    };
  }
  
  // Check budget
  if (state.budget < cost && state.mode === "enforce") {
    return { 
      allow: false, 
      reason: `Budget depleted (${state.budget.toFixed(2)}). Need ${cost} for ${risk} operation.` 
    };
  }
  
  // Soft mode only blocks HIGH+
  if (state.mode === "soft" && risk !== "HIGH" && risk !== "CRITICAL") {
    return { allow: true };
  }
  
  // Shadow mode - always allow but would log
  if (state.mode === "shadow") {
    return { allow: true };
  }
  
  return { allow: true };
}

function recordOperation(toolName: string, blocked: boolean) {
  const risk = getRiskLevel(toolName);
  const cost = getRiskCost(risk);
  
  // Deduct budget (only if not blocked and not SAFE)
  if (!blocked && risk !== "SAFE") {
    state.budget = Math.max(0, state.budget - cost);
  }
  
  state.opsSinceCheckpoint++;
  
  // Adjust trust
  if (!blocked) {
    state.trust = Math.min(1.0, state.trust + 0.005);
    state.cleanStreak++;
    if (state.cleanStreak >= 10) {
      state.trust = Math.min(1.0, state.trust + 0.01);
    }
  }
  
  // Record history
  state.history.push({
    timestamp: new Date().toISOString(),
    tool: toolName,
    risk,
    blocked,
  });
  
  // Trim history
  if (state.history.length > 100) {
    state.history = state.history.slice(-100);
  }
  
  // Send to dashboard (fire and forget)
  sendToDashboard(toolName, risk, blocked);
}

function sendToDashboard(tool: string, risk: RiskLevel, blocked: boolean) {
  if (!config.dashboardEnabled) return;
  
  try {
    fetch(`${dashboardUrl}/api/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        timestamp: new Date().toISOString(),
        operation: tool,
        risk_level: risk,
        would_block: blocked,
        actually_blocked: blocked && state.mode !== "shadow",
        reasons: blocked ? ["Budget/trust check failed"] : [],
        trust_score: state.trust,
        budget_remaining: state.budget,
      }),
    }).catch(() => {});
  } catch {
    // Dashboard not available, ignore
  }
}

function onHumanMessage() {
  // Human interaction resets budget and boosts trust
  state.budget = config.budgetSize ?? 1.0;
  state.trust = Math.min(1.0, state.trust + 0.05);
  state.lastHumanMs = Date.now();
  state.opsSinceCheckpoint = 0;
  state.cleanStreak = 0;
  
  // Notify dashboard
  if (config.dashboardEnabled) {
    try {
      fetch(`${dashboardUrl}/api/state`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: state.mode,
          trust_score: state.trust,
          budget_remaining: state.budget,
        }),
      }).catch(() => {});
    } catch {
      // ignore
    }
  }
}

export default function register(api: any) {
  // Debug: write to file to prove we loaded
  const debugPath = "/tmp/equilibrium-guard-debug.log";
  const timestamp = new Date().toISOString();
  fs.appendFileSync(debugPath, `[${timestamp}] Register called! api.on=${typeof api.on}\n`);
  
  const pluginConfig = api.config as PluginConfig;
  initState(pluginConfig);
  
  fs.appendFileSync(debugPath, `[${timestamp}] State initialized, mode=${state.mode}\n`);
  api.log?.info?.(`[equilibrium-guard] Initialized in ${state.mode} mode`);
  
  // Register before_tool_call hook using api.on() for typed hooks
  api.on(
    "before_tool_call",
    async (event: { toolName: string; params: Record<string, unknown> }) => {
      const toolName = event.toolName?.toLowerCase() ?? "unknown";
      const { allow, reason } = checkOperation(toolName);
      
      // Record the operation
      recordOperation(toolName, !allow);
      
      if (!allow && state.mode !== "shadow") {
        api.log?.warn?.(`[equilibrium-guard] Blocked: ${toolName} — ${reason}`);
        return {
          block: true,
          blockReason: reason,
        };
      }
      
      if (!allow && state.mode === "shadow") {
        api.log?.debug?.(`[equilibrium-guard] Shadow: would block ${toolName}`);
      }
      
      return {};
    },
    { name: "equilibrium-guard-before-tool" }
  );
  
  // Register message_received hook to detect human interaction
  api.on(
    "message_received",
    async () => {
      onHumanMessage();
    },
    { name: "equilibrium-guard-human-checkpoint" }
  );
  
  api.log?.info?.(`[equilibrium-guard] Plugin registered. Dashboard: ${dashboardUrl}`);
}
