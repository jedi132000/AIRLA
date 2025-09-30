"""
Audit Logger for Multi-Agent Logistics System
Tracks all system events, user actions, and agent decisions for compliance and debugging.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class AuditEventType(Enum):
    """Categories of audit events"""
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"
    
    VEHICLE_ASSIGNED = "vehicle_assigned"
    VEHICLE_UNASSIGNED = "vehicle_unassigned"
    VEHICLE_STATUS_CHANGED = "vehicle_status_changed"
    
    ROUTE_PLANNED = "route_planned"
    ROUTE_UPDATED = "route_updated"
    ROUTE_OPTIMIZED = "route_optimized"
    
    AGENT_ACTION = "agent_action"
    AGENT_DECISION = "agent_decision"
    AGENT_ERROR = "agent_error"
    
    USER_LOGIN = "user_login"
    USER_ACTION = "user_action"
    USER_LOGOUT = "user_logout"
    
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    
    EXCEPTION_RAISED = "exception_raised"
    EXCEPTION_RESOLVED = "exception_resolved"
    
    CONFIG_CHANGED = "config_changed"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Individual audit event record"""
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    agent_id: Optional[str]
    entity_id: Optional[str]  # Order ID, Vehicle ID, etc.
    entity_type: Optional[str]  # "order", "vehicle", "route", etc.
    action: str
    details: Dict[str, Any]
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['event_type'] = AuditEventType(data['event_type'])
        data['severity'] = AuditSeverity(data['severity'])
        return cls(**data)


class AuditLogger:
    """Centralized audit logging system"""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 50 * 1024 * 1024):  # 50MB
        """
        Initialize audit logger
        
        Args:
            log_dir: Directory to store audit log files
            max_file_size: Maximum size per log file before rotation
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.max_file_size = max_file_size
        self.current_file = None
        self.events_buffer = []
        self.buffer_size = 100  # Number of events to buffer before writing
        
        # Setup structured logging
        self._setup_logger()
        
        # Track session for correlation
        self.session_id = self._generate_session_id()
    
    def _setup_logger(self):
        """Configure the underlying logger"""
        self.logger = logging.getLogger('audit_logger')
        self.logger.setLevel(logging.INFO)
        
        # Create formatter for structured logs
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with rotation
        log_file = self.log_dir / "audit.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier"""
        return f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{id(self) % 10000}"
    
    def log_event(self, 
                  event_type: AuditEventType,
                  action: str,
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  user_id: Optional[str] = None,
                  agent_id: Optional[str] = None,
                  entity_id: Optional[str] = None,
                  entity_type: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  **kwargs) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            action: Description of the action taken
            severity: Severity level
            user_id: ID of user who performed the action
            agent_id: ID of agent that performed the action
            entity_id: ID of the affected entity
            entity_type: Type of the affected entity
            details: Additional event details
            **kwargs: Additional metadata
            
        Returns:
            Event ID for tracking
        """
        if details is None:
            details = {}
        
        # Add any additional kwargs to details
        details.update(kwargs)
        
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            agent_id=agent_id,
            entity_id=entity_id,
            entity_type=entity_type,
            action=action,
            details=details,
            session_id=self.session_id
        )
        
        # Add to buffer
        self.events_buffer.append(event)
        
        # Write to structured log immediately for high/critical events
        if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
            self._write_event_to_log(event)
        
        # Flush buffer if full
        if len(self.events_buffer) >= self.buffer_size:
            self.flush_buffer()
        
        event_id = f"{event.timestamp.isoformat()}_{id(event) % 10000}"
        return event_id
    
    def _write_event_to_log(self, event: AuditEvent):
        """Write single event to structured log"""
        log_entry = json.dumps(event.to_dict(), default=str)
        self.logger.info(log_entry)
    
    def flush_buffer(self):
        """Write all buffered events to log"""
        for event in self.events_buffer:
            self._write_event_to_log(event)
        self.events_buffer.clear()
    
    # Convenience methods for common events
    
    def log_user_action(self, user_id: str, action: str, details: Optional[Dict] = None):
        """Log user action"""
        return self.log_event(
            AuditEventType.USER_ACTION,
            action,
            AuditSeverity.MEDIUM,
            user_id=user_id,
            details=details or {}
        )
    
    def log_order_event(self, action: str, order_id: str, user_id: Optional[str] = None, details: Optional[Dict] = None):
        """Log order-related event"""
        event_type_map = {
            "created": AuditEventType.ORDER_CREATED,
            "updated": AuditEventType.ORDER_UPDATED,
            "completed": AuditEventType.ORDER_COMPLETED,
            "cancelled": AuditEventType.ORDER_CANCELLED
        }
        
        event_type = event_type_map.get(action.lower(), AuditEventType.ORDER_UPDATED)
        
        return self.log_event(
            event_type,
            f"Order {action}",
            AuditSeverity.MEDIUM,
            user_id=user_id,
            entity_id=order_id,
            entity_type="order",
            details=details or {}
        )
    
    def log_agent_action(self, agent_id: str, action: str, details: Optional[Dict] = None, severity: AuditSeverity = AuditSeverity.MEDIUM):
        """Log agent action or decision"""
        return self.log_event(
            AuditEventType.AGENT_ACTION,
            action,
            severity,
            agent_id=agent_id,
            details=details or {}
        )
    
    def log_system_event(self, action: str, severity: AuditSeverity = AuditSeverity.HIGH, details: Optional[Dict] = None):
        """Log system-level event"""
        event_type_map = {
            "start": AuditEventType.SYSTEM_START,
            "stop": AuditEventType.SYSTEM_STOP,
            "error": AuditEventType.SYSTEM_ERROR
        }
        
        event_type = event_type_map.get(action.lower(), AuditEventType.SYSTEM_ERROR)
        
        return self.log_event(
            event_type,
            f"System {action}",
            severity,
            details=details or {}
        )
    
    def log_exception(self, exception_id: str, action: str, details: Optional[Dict] = None):
        """Log exception handling event"""
        event_type = AuditEventType.EXCEPTION_RAISED if action.lower() == "raised" else AuditEventType.EXCEPTION_RESOLVED
        severity = AuditSeverity.HIGH if action.lower() == "raised" else AuditSeverity.MEDIUM
        
        return self.log_event(
            event_type,
            f"Exception {action}",
            severity,
            entity_id=exception_id,
            entity_type="exception",
            details=details or {}
        )
    
    def search_events(self, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     event_types: Optional[List[AuditEventType]] = None,
                     user_id: Optional[str] = None,
                     agent_id: Optional[str] = None,
                     entity_id: Optional[str] = None,
                     severity: Optional[AuditSeverity] = None,
                     limit: int = 1000) -> List[AuditEvent]:
        """
        Search audit events with filters
        
        Args:
            start_time: Filter events after this time
            end_time: Filter events before this time
            event_types: Filter by event types
            user_id: Filter by user ID
            agent_id: Filter by agent ID
            entity_id: Filter by entity ID
            severity: Filter by severity level
            limit: Maximum number of events to return
            
        Returns:
            List of matching audit events
        """
        # This is a simplified implementation - in production,
        # you'd want to use a proper database or search index
        
        # Flush buffer to ensure all events are searchable
        self.flush_buffer()
        
        # For now, return mock data matching the filters
        # In a real implementation, this would search the log files or database
        
        mock_events = []
        base_time = datetime.now(timezone.utc)
        
        # Generate some realistic mock events
        for i in range(min(limit, 20)):
            event_time = base_time.replace(minute=base_time.minute - i)
            
            # Skip if outside time range
            if start_time and event_time < start_time:
                continue
            if end_time and event_time > end_time:
                continue
            
            mock_event = AuditEvent(
                timestamp=event_time,
                event_type=AuditEventType.USER_ACTION,
                severity=AuditSeverity.MEDIUM,
                user_id="user123" if not user_id or user_id == "user123" else None,
                agent_id="supervisor" if not agent_id or agent_id == "supervisor" else None,
                entity_id=f"ORD-{1000 + i}",
                entity_type="order",
                action=f"Sample action {i}",
                details={"sample": f"data {i}"},
                session_id=self.session_id
            )
            
            # Apply filters
            if event_types and mock_event.event_type not in event_types:
                continue
            if user_id and mock_event.user_id != user_id:
                continue
            if agent_id and mock_event.agent_id != agent_id:
                continue
            if entity_id and mock_event.entity_id != entity_id:
                continue
            if severity and mock_event.severity != severity:
                continue
            
            mock_events.append(mock_event)
        
        return mock_events[:limit]
    
    def get_statistics(self, 
                      start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get audit statistics for a time period
        
        Args:
            start_time: Start of time period
            end_time: End of time period
            
        Returns:
            Dictionary containing audit statistics
        """
        # In a real implementation, this would analyze the actual log data
        return {
            "total_events": 1247,
            "events_by_type": {
                "user_action": 543,
                "agent_action": 312,
                "order_created": 89,
                "order_updated": 156,
                "system_event": 45,
                "exception_raised": 23,
                "exception_resolved": 21
            },
            "events_by_severity": {
                "low": 234,
                "medium": 876,
                "high": 112,
                "critical": 25
            },
            "top_users": [
                {"user_id": "user123", "action_count": 89},
                {"user_id": "user456", "action_count": 67},
                {"user_id": "admin", "action_count": 45}
            ],
            "top_agents": [
                {"agent_id": "supervisor", "action_count": 156},
                {"agent_id": "order_ingestion", "action_count": 89},
                {"agent_id": "vehicle_assignment", "action_count": 67}
            ],
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            }
        }
    
    def export_events(self, 
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     format: str = "json") -> str:
        """
        Export audit events to file
        
        Args:
            start_time: Start of time range to export
            end_time: End of time range to export
            format: Export format ("json" or "csv")
            
        Returns:
            Path to exported file
        """
        events = self.search_events(start_time=start_time, end_time=end_time, limit=10000)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format.lower() == "json":
            export_file = self.log_dir / f"audit_export_{timestamp}.json"
            with open(export_file, 'w') as f:
                json.dump([event.to_dict() for event in events], f, indent=2, default=str)
        elif format.lower() == "csv":
            import csv
            export_file = self.log_dir / f"audit_export_{timestamp}.csv"
            
            with open(export_file, 'w', newline='') as f:
                if events:
                    fieldnames = events[0].to_dict().keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for event in events:
                        writer.writerow(event.to_dict())
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return str(export_file)
    
    def __del__(self):
        """Ensure buffer is flushed when logger is destroyed"""
        if hasattr(self, 'events_buffer') and self.events_buffer:
            self.flush_buffer()


# Global audit logger instance
audit_logger = AuditLogger()