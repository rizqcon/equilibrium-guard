#!/usr/bin/env python3
"""
Equilibrium Guard Dashboard — Real-time Security Monitor
=========================================================

WebSocket-based dashboard for monitoring AI agent operations.

Run:
    python dashboard/server.py

Then open: http://localhost:8081
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DecisionEvent:
    """A decision event for the dashboard."""
    id: str
    timestamp: str
    operation: str
    risk_level: str
    would_block: bool
    actually_blocked: bool
    reasons: List[str]
    trust_score: float
    budget_remaining: float
    parent_id: str = None  # For storyline linking
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DriftAlert:
    """A drift detection alert."""
    id: str
    timestamp: str
    pattern: str
    description: str
    severity: str
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GuardState:
    """Current state of the guard."""
    mode: str
    trust_score: float
    budget_remaining: float
    total_decisions: int
    blocked_count: int
    would_block_count: int
    active_alerts: int


# =============================================================================
# DASHBOARD STATE
# =============================================================================

class DashboardState:
    """Holds all dashboard state."""
    
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.decisions: deque = deque(maxlen=max_history)
        self.alerts: List[DriftAlert] = []
        self.decision_counter = 0
        self.alert_counter = 0
        
        # Current guard state
        self.mode = "shadow"
        self.trust_score = 0.7
        self.budget_remaining = 1.0
        self.blocked_count = 0
        self.would_block_count = 0
        
        # Mind map nodes (operation -> count)
        self.operation_graph: Dict[str, Dict] = {}
        
        # Last operation for storyline linking
        self.last_operation_id: str = None
    
    def add_decision(self, event: DecisionEvent) -> DecisionEvent:
        """Add a decision and return it with ID assigned."""
        self.decision_counter += 1
        event.id = f"d_{self.decision_counter}"
        event.parent_id = self.last_operation_id
        
        self.decisions.append(event)
        self.last_operation_id = event.id
        
        # Update stats
        if event.actually_blocked:
            self.blocked_count += 1
        if event.would_block:
            self.would_block_count += 1
        
        # Update state
        self.trust_score = event.trust_score
        self.budget_remaining = event.budget_remaining
        
        # Update operation graph for mind map
        op = event.operation
        if op not in self.operation_graph:
            self.operation_graph[op] = {
                "count": 0,
                "blocked": 0,
                "risk_levels": {},
            }
        self.operation_graph[op]["count"] += 1
        if event.actually_blocked:
            self.operation_graph[op]["blocked"] += 1
        
        risk = event.risk_level
        if risk not in self.operation_graph[op]["risk_levels"]:
            self.operation_graph[op]["risk_levels"][risk] = 0
        self.operation_graph[op]["risk_levels"][risk] += 1
        
        return event
    
    def add_alert(self, pattern: str, description: str, severity: str) -> DriftAlert:
        """Add a drift alert."""
        self.alert_counter += 1
        alert = DriftAlert(
            id=f"a_{self.alert_counter}",
            timestamp=datetime.now().isoformat(),
            pattern=pattern,
            description=description,
            severity=severity,
        )
        self.alerts.append(alert)
        return alert
    
    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                break
    
    def get_state(self) -> GuardState:
        """Get current state summary."""
        active_alerts = len([a for a in self.alerts if not a.acknowledged])
        return GuardState(
            mode=self.mode,
            trust_score=self.trust_score,
            budget_remaining=self.budget_remaining,
            total_decisions=self.decision_counter,
            blocked_count=self.blocked_count,
            would_block_count=self.would_block_count,
            active_alerts=active_alerts,
        )
    
    def get_recent_decisions(self, n: int = 50) -> List[Dict]:
        """Get recent decisions."""
        return [d.to_dict() for d in list(self.decisions)[-n:]]
    
    def get_mind_map_data(self) -> Dict:
        """Get data for mind map visualization."""
        return {
            "operations": self.operation_graph,
            "total_decisions": self.decision_counter,
        }
    
    def set_mode(self, mode: str):
        """Set guard mode."""
        self.mode = mode
    
    def checkpoint(self):
        """Human checkpoint — reset budget."""
        self.budget_remaining = 1.0
        self.last_operation_id = None  # Break storyline chain


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected
        self.active_connections -= disconnected


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(title="Equilibrium Guard Dashboard")
state = DashboardState()
manager = ConnectionManager()

# Serve static files
dashboard_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=dashboard_dir / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard HTML."""
    html_path = dashboard_dir / "templates" / "dashboard.html"
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    # Send initial state
    await websocket.send_json({
        "type": "init",
        "state": asdict(state.get_state()),
        "decisions": state.get_recent_decisions(50),
        "alerts": [a.to_dict() for a in state.alerts if not a.acknowledged],
        "mindmap": state.get_mind_map_data(),
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, data: Dict):
    """Handle incoming client messages."""
    msg_type = data.get("type")
    
    if msg_type == "set_mode":
        mode = data.get("mode", "shadow")
        state.set_mode(mode)
        await manager.broadcast({
            "type": "mode_changed",
            "mode": mode,
        })
    
    elif msg_type == "checkpoint":
        state.checkpoint()
        await manager.broadcast({
            "type": "checkpoint",
            "budget": state.budget_remaining,
        })
    
    elif msg_type == "acknowledge_alert":
        alert_id = data.get("alert_id")
        state.acknowledge_alert(alert_id)
        await manager.broadcast({
            "type": "alert_acknowledged",
            "alert_id": alert_id,
        })
    
    elif msg_type == "get_state":
        await websocket.send_json({
            "type": "state",
            "state": asdict(state.get_state()),
        })


# =============================================================================
# API FOR GUARD INTEGRATION
# =============================================================================

@app.post("/api/decision")
async def post_decision(decision: Dict[str, Any]):
    """Receive a decision from the guard."""
    event = DecisionEvent(
        id="",  # Will be assigned
        timestamp=decision.get("timestamp", datetime.now().isoformat()),
        operation=decision.get("operation", "unknown"),
        risk_level=decision.get("risk_level", "SAFE"),
        would_block=decision.get("would_block", False),
        actually_blocked=decision.get("actually_blocked", False),
        reasons=decision.get("reasons", []),
        trust_score=decision.get("trust_score", 0.7),
        budget_remaining=decision.get("budget_remaining", 1.0),
    )
    
    event = state.add_decision(event)
    
    # Broadcast to all clients
    await manager.broadcast({
        "type": "decision",
        "decision": event.to_dict(),
        "state": asdict(state.get_state()),
    })
    
    return {"status": "ok", "id": event.id}


@app.post("/api/alert")
async def post_alert(alert: Dict[str, Any]):
    """Receive a drift alert from the guard."""
    drift_alert = state.add_alert(
        pattern=alert.get("pattern", "unknown"),
        description=alert.get("description", ""),
        severity=alert.get("severity", "warning"),
    )
    
    # Broadcast to all clients
    await manager.broadcast({
        "type": "alert",
        "alert": drift_alert.to_dict(),
    })
    
    return {"status": "ok", "id": drift_alert.id}


@app.post("/api/state")
async def post_state(update: Dict[str, Any]):
    """Update guard state."""
    if "mode" in update:
        state.set_mode(update["mode"])
    if "trust_score" in update:
        state.trust_score = update["trust_score"]
    if "budget_remaining" in update:
        state.budget_remaining = update["budget_remaining"]
    
    await manager.broadcast({
        "type": "state_update",
        "state": asdict(state.get_state()),
    })
    
    return {"status": "ok"}


@app.get("/api/state")
async def get_state():
    """Get current state."""
    return {
        "state": asdict(state.get_state()),
        "mindmap": state.get_mind_map_data(),
    }


@app.get("/api/decisions")
async def get_decisions(limit: int = 100):
    """Get recent decisions."""
    return {"decisions": state.get_recent_decisions(limit)}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EQUILIBRIUM GUARD DASHBOARD")
    print("=" * 60)
    print("\nStarting server on http://localhost:8081")
    print("WebSocket endpoint: ws://localhost:8081/ws")
    print("\nAPI endpoints:")
    print("  POST /api/decision  - Submit decision from guard")
    print("  POST /api/alert     - Submit drift alert")
    print("  POST /api/state     - Update guard state")
    print("  GET  /api/state     - Get current state")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8081)
