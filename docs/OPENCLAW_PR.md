# PR: Wire up `before_tool_call` hook for plugin interception

## Summary

The `before_tool_call` hook is defined in `plugins/hooks.js` but never called in the tool execution flow. This PR wires it up so plugins can intercept and optionally block tool calls.

## Use Case

Security/guardrail plugins like Equilibrium Guard need to intercept tool calls before execution to:
- Enforce risk-based autonomy budgets
- Block operations that exceed trust thresholds
- Log all tool invocations for audit trails
- Implement zero-trust patterns for AI agents

## Current State

```
/dist/plugins/hooks.js:152: runBeforeToolCall  ← Defined
/dist/agents/steerable-agent-loop.js          ← Never called
```

## Proposed Change

**File:** `src/agents/steerable-agent-loop.ts` (or `.js` in dist)

**Location:** Inside `executeToolCalls()`, before `tool.execute()` is called (~line 254)

### Before:
```typescript
try {
    if (!tool) throw new Error(`Tool ${toolCall.name} not found`);
    const validatedArgs = validateToolArguments(tool, toolCall);
    result = await tool.execute(toolCall.id, validatedArgs, signal, ...);
```

### After:
```typescript
try {
    if (!tool) throw new Error(`Tool ${toolCall.name} not found`);
    const validatedArgs = validateToolArguments(tool, toolCall);
    
    // Run before_tool_call hook - allows plugins to block or modify
    if (hookRunner?.hasHooks?.("before_tool_call")) {
        const hookResult = await hookRunner.runBeforeToolCall({
            toolName: toolCall.name,
            toolCallId: toolCall.id,
            params: validatedArgs,
        }, { /* context */ });
        
        if (hookResult?.block) {
            throw new Error(hookResult.blockReason ?? `Tool ${toolCall.name} blocked by plugin`);
        }
        
        // Allow plugins to modify params
        if (hookResult?.params) {
            Object.assign(validatedArgs, hookResult.params);
        }
    }
    
    result = await tool.execute(toolCall.id, validatedArgs, signal, ...);
```

## Hook Contract

The hook receives:
```typescript
interface BeforeToolCallEvent {
    toolName: string;
    toolCallId: string;
    params: Record<string, unknown>;
}
```

The hook can return:
```typescript
interface BeforeToolCallResult {
    block?: boolean;        // If true, throw error instead of executing
    blockReason?: string;   // Error message when blocked
    params?: Record<string, unknown>;  // Modified params (merged)
}
```

## Also Needed

The `hookRunner` needs to be passed into `executeToolCalls()` or available in scope. This may require threading it through from the agent context.

## Testing

1. Create a test plugin that registers `before_tool_call` hook
2. Verify it receives all tool calls
3. Verify `block: true` prevents execution
4. Verify `params` modifications are applied

## Backwards Compatible

Yes - if no hooks are registered, behavior is unchanged (the `hasHooks` check short-circuits).

---

**Related:** This enables plugins like [Equilibrium Guard](https://github.com/rizqcon/equilibrium-guard) to provide zero-trust guardrails for AI agents.
