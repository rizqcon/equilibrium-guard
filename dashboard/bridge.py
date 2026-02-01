"""
Equilibrium Guard Dashboard Bridge
===================================

Connects the EquilibriumGuard to the dashboard via HTTP/WebSocket.

Usage:
    from equilibrium_guard import create_guard
    from dashboard.bridge import DashboardBridge
    
    guard = create_guard(mode='shadow')
    bridge = DashboardBridge(guard, dashboard_url='http://localhost:8081')
    bridge.connect()
    
    # Now all decisions are sent to the dashboard in real-time
"""

import asyncio
import threading
import queue
from typing import Optional
from datetime import datetime
import requests


class DashboardBridge:
    """
    Bridges EquilibriumGuard to the dashboard.
    
    Sends decisions and alerts to the dashboard API in real-time.
    """
    
    def __init__(
        self,
        guard,
        dashboard_url: str = 'http://localhost:8081',
        async_mode: bool = True,
    ):
        """
        Initialize the bridge.
        
        Args:
            guard: EquilibriumGuard instance
            dashboard_url: Dashboard API URL
            async_mode: If True, send events asynchronously
        """
        self.guard = guard
        self.dashboard_url = dashboard_url.rstrip('/')
        self.async_mode = async_mode
        
        self._connected = False
        self._queue: Optional[queue.Queue] = None
        self._thread: Optional[threading.Thread] = None
    
    def connect(self):
        """Connect the bridge and start sending events."""
        if self._connected:
            return
        
        # Register decision callback
        self.guard.on_decision(self._on_decision)
        
        # Register drift callback on anchor
        self.guard.anchor.on_violation(self._on_drift)
        
        if self.async_mode:
            self._queue = queue.Queue()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
        
        # Send initial state
        self._send_state()
        
        self._connected = True
        print(f"[DashboardBridge] Connected to {self.dashboard_url}")
    
    def disconnect(self):
        """Disconnect the bridge."""
        self._connected = False
        if self._queue:
            self._queue.put(None)  # Signal to stop
    
    def _on_decision(self, decision):
        """Handle decision events from the guard."""
        data = {
            'timestamp': decision.timestamp.isoformat(),
            'operation': decision.operation,
            'risk_level': decision.risk_level,
            'would_block': decision.would_block,
            'actually_blocked': decision.actually_blocked,
            'reasons': decision.reasons,
            'trust_score': decision.trust_score,
            'budget_remaining': decision.budget_remaining,
        }
        
        if self.async_mode:
            self._queue.put(('decision', data))
        else:
            self._send_decision(data)
    
    def _on_drift(self, violation_type: str, details: dict):
        """Handle drift detection events."""
        data = {
            'pattern': violation_type,
            'description': details.get('description', str(details)),
            'severity': details.get('severity', 'warning'),
        }
        
        if self.async_mode:
            self._queue.put(('alert', data))
        else:
            self._send_alert(data)
    
    def _send_decision(self, data: dict):
        """Send decision to dashboard."""
        try:
            requests.post(
                f"{self.dashboard_url}/api/decision",
                json=data,
                timeout=1,
            )
        except Exception as e:
            print(f"[DashboardBridge] Failed to send decision: {e}")
    
    def _send_alert(self, data: dict):
        """Send alert to dashboard."""
        try:
            requests.post(
                f"{self.dashboard_url}/api/alert",
                json=data,
                timeout=1,
            )
        except Exception as e:
            print(f"[DashboardBridge] Failed to send alert: {e}")
    
    def _send_state(self):
        """Send current state to dashboard."""
        try:
            state = self.guard.anchor.state
            requests.post(
                f"{self.dashboard_url}/api/state",
                json={
                    'mode': self.guard.mode.value,
                    'trust_score': state.trust_score,
                    'budget_remaining': state.risk_budget,
                },
                timeout=1,
            )
        except Exception as e:
            print(f"[DashboardBridge] Failed to send state: {e}")
    
    def _worker(self):
        """Background worker for async sending."""
        while True:
            item = self._queue.get()
            
            if item is None:
                break
            
            event_type, data = item
            
            if event_type == 'decision':
                self._send_decision(data)
            elif event_type == 'alert':
                self._send_alert(data)
            elif event_type == 'state':
                self._send_state()


def connect_to_dashboard(
    guard,
    dashboard_url: str = 'http://localhost:8081',
) -> DashboardBridge:
    """
    Convenience function to connect a guard to the dashboard.
    
    Usage:
        guard = create_guard()
        bridge = connect_to_dashboard(guard)
    """
    bridge = DashboardBridge(guard, dashboard_url)
    bridge.connect()
    return bridge
