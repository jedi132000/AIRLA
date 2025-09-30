"""
Notification System for AI Logistics Dashboard
Handles real-time notifications, alerts, and in-app messaging
"""

import streamlit as st
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


class NotificationType(Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class Notification:
    """Individual notification object"""
    id: str
    title: str
    message: str
    type: NotificationType
    priority: NotificationPriority
    timestamp: datetime
    read: bool = False
    dismissed: bool = False
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationManager:
    """Manages notifications throughout the application"""
    
    def __init__(self):
        self.notifications = []
        self.max_notifications = 100
        
    def add_notification(self, 
                        title: str, 
                        message: str,
                        type: NotificationType = NotificationType.INFO,
                        priority: NotificationPriority = NotificationPriority.MEDIUM,
                        action_url: Optional[str] = None,
                        action_label: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new notification"""
        notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.notifications)}"
        
        notification = Notification(
            id=notification_id,
            title=title,
            message=message,
            type=type,
            priority=priority,
            timestamp=datetime.now(),
            action_url=action_url,
            action_label=action_label,
            metadata=metadata or {}
        )
        
        # Add to beginning of list (newest first)
        self.notifications.insert(0, notification)
        
        # Trim to max notifications
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]
        
        return notification_id
    
    def get_notifications(self, unread_only: bool = False, limit: Optional[int] = None) -> List[Notification]:
        """Get notifications with optional filters"""
        notifications = self.notifications
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        if limit:
            notifications = notifications[:limit]
            
        return notifications
    
    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.read = True
                return True
        return False
    
    def dismiss(self, notification_id: str) -> bool:
        """Dismiss a notification"""
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.dismissed = True
                return True
        return False
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        return len([n for n in self.notifications if not n.read and not n.dismissed])
    
    def get_critical_count(self) -> int:
        """Get count of critical notifications"""
        return len([n for n in self.notifications if n.priority == NotificationPriority.CRITICAL and not n.dismissed])
    
    def clear_old_notifications(self, older_than_days: int = 7):
        """Clear notifications older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        self.notifications = [n for n in self.notifications if n.timestamp > cutoff_date]
    
    def render_notification_center(self):
        """Render the notification center UI"""
        st.subheader("🔔 Notification Center")
        
        # Notification filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            show_unread_only = st.checkbox("Show unread only", value=False)
        with col2:
            notification_limit = st.selectbox("Limit", [10, 25, 50, 100], index=1)
        with col3:
            if st.button("Mark All Read"):
                for notification in self.notifications:
                    notification.read = True
                st.success("All notifications marked as read")
        
        # Get filtered notifications
        notifications = self.get_notifications(unread_only=show_unread_only, limit=notification_limit)
        
        if not notifications:
            st.info("No notifications to display")
            return
        
        # Render notifications
        for notification in notifications:
            self._render_notification(notification)
    
    def _render_notification(self, notification: Notification):
        """Render a single notification"""
        # Color coding based on type and priority
        type_colors = {
            NotificationType.INFO: "blue",
            NotificationType.SUCCESS: "green", 
            NotificationType.WARNING: "orange",
            NotificationType.ERROR: "red",
            NotificationType.CRITICAL: "red"
        }
        
        priority_icons = {
            NotificationPriority.LOW: "🔵",
            NotificationPriority.MEDIUM: "🟡",
            NotificationPriority.HIGH: "🟠", 
            NotificationPriority.URGENT: "🔴",
            NotificationPriority.CRITICAL: "🚨"
        }
        
        with st.expander(
            f"{priority_icons.get(notification.priority, '📋')} {notification.title}", 
            expanded=(notification.priority.value >= 4 and not notification.read)
        ):
            # Notification content
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(notification.message)
                st.caption(f"⏰ {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show metadata if available
                if notification.metadata:
                    with st.expander("📋 Details"):
                        st.json(notification.metadata)
            
            with col2:
                # Action buttons
                if not notification.read:
                    if st.button(f"✅ Mark Read", key=f"read_{notification.id}"):
                        self.mark_read(notification.id)
                        st.rerun()
                
                if not notification.dismissed:
                    if st.button(f"❌ Dismiss", key=f"dismiss_{notification.id}"):
                        self.dismiss(notification.id)
                        st.rerun()
                
                # Action button if specified
                if notification.action_url and notification.action_label:
                    if st.button(f"🔗 {notification.action_label}", key=f"action_{notification.id}"):
                        st.info(f"Action triggered: {notification.action_url}")
    
    def render_notification_badge(self):
        """Render a notification badge for the header"""
        unread_count = self.get_unread_count()
        critical_count = self.get_critical_count()
        
        if critical_count > 0:
            st.error(f"🚨 {critical_count} Critical Alerts")
        elif unread_count > 0:
            st.warning(f"🔔 {unread_count} New Notifications")
        else:
            st.success("🔔 No New Alerts")
    
    def add_system_notifications(self):
        """Add sample system notifications for demonstration"""
        # Critical system alerts
        self.add_notification(
            "System Performance Alert",
            "CPU usage has exceeded 85% for the last 15 minutes. Consider scaling resources.",
            NotificationType.CRITICAL,
            NotificationPriority.CRITICAL,
            metadata={"cpu_usage": 87.3, "duration": 15, "threshold": 85}
        )
        
        # Order notifications
        self.add_notification(
            "High Priority Order Assigned",
            "Order ORD-001234 (Priority 5) has been assigned to Vehicle VH-007 and is now en route.",
            NotificationType.SUCCESS,
            NotificationPriority.HIGH,
            action_url="/orders/ORD-001234",
            action_label="View Order",
            metadata={"order_id": "ORD-001234", "vehicle_id": "VH-007", "priority": 5}
        )
        
        # Vehicle notifications
        self.add_notification(
            "Vehicle Maintenance Due",
            "Vehicle VH-015 is due for scheduled maintenance in 2 days. Please schedule service.",
            NotificationType.WARNING,
            NotificationPriority.MEDIUM,
            metadata={"vehicle_id": "VH-015", "maintenance_type": "scheduled", "days_remaining": 2}
        )
        
        # Route optimization
        self.add_notification(
            "Route Optimization Complete",
            "AI agent has optimized routes for 12 vehicles, saving an estimated 45 minutes total delivery time.",
            NotificationType.SUCCESS,
            NotificationPriority.LOW,
            metadata={"vehicles_optimized": 12, "time_saved_minutes": 45, "efficiency_gain": "12%"}
        )
        
        # Traffic alerts
        self.add_notification(
            "Traffic Delay Detected",
            "Heavy traffic on I-95 North is causing delays. 3 vehicles affected, ETAs updated automatically.",
            NotificationType.WARNING,
            NotificationPriority.MEDIUM,
            metadata={"affected_vehicles": ["VH-003", "VH-008", "VH-012"], "delay_minutes": 20}
        )


# Global notification manager
notification_manager = NotificationManager()

# Initialize with sample notifications
notification_manager.add_system_notifications()