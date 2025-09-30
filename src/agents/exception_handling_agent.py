"""
Exception Handling Agent - Responds to failed deliveries, reroutes, and escalates problems.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

from base_agent import BaseAgent
from models import Order, Vehicle, OrderState, VehicleState, AgentState


class ExceptionType(str, Enum):
    """Types of exceptions that can occur"""
    DELIVERY_FAILURE = "delivery_failure"
    VEHICLE_BREAKDOWN = "vehicle_breakdown"
    TIME_WINDOW_VIOLATION = "time_window_violation"
    CUSTOMER_UNAVAILABLE = "customer_unavailable"
    ADDRESS_INVALID = "address_invalid"
    TRAFFIC_DELAY = "traffic_delay"
    WEATHER_DELAY = "weather_delay"
    CAPACITY_EXCEEDED = "capacity_exceeded"


class ExceptionSeverity(str, Enum):
    """Severity levels for exceptions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExceptionHandlingAgent(BaseAgent):
    """
    Handles exceptions, failures, and emergency situations in the logistics system.
    Implements escalation procedures and recovery strategies.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("exception_handling_agent", state_manager, llm)
        self.active_exceptions = {}
        self.exception_history = []
        self.escalation_rules = self._setup_escalation_rules()
        self.recovery_strategies = self._setup_recovery_strategies()
        self.emergency_protocols_active = False
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process exception handling requests"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            action = input_data.get("action", "handle_exception")
            
            if action == "handle_exception":
                result = self._handle_exception(input_data)
            elif action == "escalate_exception":
                result = self._escalate_exception(input_data)
            elif action == "emergency_activation":
                result = self._activate_emergency_protocols(input_data)
            elif action == "recover_from_failure":
                result = self._recover_from_failure(input_data)
            elif action == "review_exceptions":
                result = self._review_active_exceptions()
            else:
                result = self._general_exception_monitoring()
            
            return result
            
        except Exception as e:
            logger.error(f"Exception handling agent error: {e}")
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _setup_escalation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Setup escalation rules for different exception types"""
        return {
            ExceptionType.DELIVERY_FAILURE: {
                "auto_escalate_after_minutes": 15,
                "max_retry_attempts": 3,
                "escalation_path": ["supervisor_agent", "customer_service"],
                "severity_multiplier": 1.0
            },
            ExceptionType.VEHICLE_BREAKDOWN: {
                "auto_escalate_after_minutes": 5,
                "max_retry_attempts": 1,
                "escalation_path": ["supervisor_agent", "fleet_management"],
                "severity_multiplier": 2.0
            },
            ExceptionType.TIME_WINDOW_VIOLATION: {
                "auto_escalate_after_minutes": 0,  # Immediate escalation
                "max_retry_attempts": 2,
                "escalation_path": ["supervisor_agent", "customer_service"],
                "severity_multiplier": 1.5
            },
            ExceptionType.TRAFFIC_DELAY: {
                "auto_escalate_after_minutes": 30,
                "max_retry_attempts": 2,
                "escalation_path": ["route_planning_agent", "supervisor_agent"],
                "severity_multiplier": 0.5
            },
            ExceptionType.WEATHER_DELAY: {
                "auto_escalate_after_minutes": 20,
                "max_retry_attempts": 1,
                "escalation_path": ["route_planning_agent", "supervisor_agent"],
                "severity_multiplier": 0.8
            }
        }
    
    def _setup_recovery_strategies(self) -> Dict[str, List[str]]:
        """Setup recovery strategies for different exception types"""
        return {
            ExceptionType.DELIVERY_FAILURE: [
                "retry_delivery",
                "reschedule_delivery",
                "reassign_vehicle",
                "contact_customer"
            ],
            ExceptionType.VEHICLE_BREAKDOWN: [
                "dispatch_replacement_vehicle",
                "reassign_orders_to_other_vehicles",
                "contact_maintenance",
                "activate_backup_fleet"
            ],
            ExceptionType.TIME_WINDOW_VIOLATION: [
                "prioritize_order",
                "contact_customer_for_extension",
                "expedite_delivery",
                "offer_compensation"
            ],
            ExceptionType.TRAFFIC_DELAY: [
                "calculate_alternative_route",
                "adjust_delivery_sequence",
                "notify_affected_customers",
                "update_estimated_times"
            ],
            ExceptionType.WEATHER_DELAY: [
                "postpone_non_urgent_deliveries",
                "use_weather_resistant_vehicles",
                "notify_customers_of_delays",
                "activate_indoor_waiting_areas"
            ]
        }
    
    def _handle_exception(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a new exception"""
        exception_data = input_data.get("exception", {})
        
        # Create exception record
        exception_id = f"EXC_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_exceptions):03d}"
        
        exception_record = {
            "id": exception_id,
            "type": exception_data.get("type", ExceptionType.DELIVERY_FAILURE),
            "severity": self._determine_severity(exception_data),
            "order_id": exception_data.get("order_id"),
            "vehicle_id": exception_data.get("vehicle_id"),
            "description": exception_data.get("description", ""),
            "occurred_at": datetime.now(),
            "status": "active",
            "retry_count": 0,
            "escalation_level": 0,
            "recovery_attempts": [],
            "assigned_handler": self.name
        }
        
        # Store active exception
        self.active_exceptions[exception_id] = exception_record
        
        # Determine initial response
        initial_response = self._determine_initial_response(exception_record)
        
        # Execute initial response
        response_result = self._execute_recovery_action(exception_record, initial_response)
        
        # Update exception record
        exception_record["recovery_attempts"].append({
            "action": initial_response,
            "executed_at": datetime.now(),
            "result": response_result
        })
        
        # Check if escalation is needed
        if self._should_escalate(exception_record):
            escalation_result = self._escalate_exception({"exception_id": exception_id})
        else:
            escalation_result = {"escalation": "not_required"}
        
        result = {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "exception_id": exception_id,
            "exception_type": exception_record["type"],
            "severity": exception_record["severity"],
            "initial_response": initial_response,
            "response_result": response_result,
            "escalation": escalation_result
        }
        
        logger.warning(f"Exception handled: {exception_id} - {exception_record['type']}")
        return result
    
    def _determine_severity(self, exception_data: Dict[str, Any]) -> ExceptionSeverity:
        """Determine the severity of an exception"""
        exception_type = exception_data.get("type", ExceptionType.DELIVERY_FAILURE)
        
        # Base severity by type
        base_severities = {
            ExceptionType.DELIVERY_FAILURE: ExceptionSeverity.MEDIUM,
            ExceptionType.VEHICLE_BREAKDOWN: ExceptionSeverity.HIGH,
            ExceptionType.TIME_WINDOW_VIOLATION: ExceptionSeverity.HIGH,
            ExceptionType.CUSTOMER_UNAVAILABLE: ExceptionSeverity.LOW,
            ExceptionType.ADDRESS_INVALID: ExceptionSeverity.MEDIUM,
            ExceptionType.TRAFFIC_DELAY: ExceptionSeverity.LOW,
            ExceptionType.WEATHER_DELAY: ExceptionSeverity.MEDIUM,
            ExceptionType.CAPACITY_EXCEEDED: ExceptionSeverity.MEDIUM
        }
        
        severity = base_severities.get(exception_type, ExceptionSeverity.MEDIUM)
        
        # Adjust based on additional factors
        if exception_data.get("customer_priority") == "high":
            if severity == ExceptionSeverity.LOW:
                severity = ExceptionSeverity.MEDIUM
            elif severity == ExceptionSeverity.MEDIUM:
                severity = ExceptionSeverity.HIGH
        
        if exception_data.get("time_sensitive", False):
            if severity == ExceptionSeverity.LOW:
                severity = ExceptionSeverity.MEDIUM
            elif severity == ExceptionSeverity.MEDIUM:
                severity = ExceptionSeverity.HIGH
            elif severity == ExceptionSeverity.HIGH:
                severity = ExceptionSeverity.CRITICAL
        
        return severity
    
    def _determine_initial_response(self, exception_record: Dict[str, Any]) -> str:
        """Determine the initial recovery action"""
        exception_type = exception_record["type"]
        severity = exception_record["severity"]
        
        strategies = self.recovery_strategies.get(exception_type, ["retry_delivery"])
        
        # Choose strategy based on severity
        if severity == ExceptionSeverity.CRITICAL:
            return strategies[0]  # Most aggressive action
        elif severity == ExceptionSeverity.HIGH:
            return strategies[0] if len(strategies) > 0 else "escalate"
        else:
            return strategies[0] if strategies else "retry_delivery"
    
    def _execute_recovery_action(self, exception_record: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Execute a recovery action"""
        order_id = exception_record.get("order_id")
        vehicle_id = exception_record.get("vehicle_id")
        
        try:
            if action == "retry_delivery":
                return self._retry_delivery(order_id, vehicle_id)
            
            elif action == "reschedule_delivery":
                return self._reschedule_delivery(order_id)
            
            elif action == "reassign_vehicle":
                return self._reassign_vehicle(order_id)
            
            elif action == "dispatch_replacement_vehicle":
                return self._dispatch_replacement_vehicle(vehicle_id)
            
            elif action == "calculate_alternative_route":
                return self._request_alternative_route(vehicle_id)
            
            elif action == "contact_customer":
                return self._contact_customer(order_id)
            
            else:
                return {"status": "action_not_implemented", "action": action}
                
        except Exception as e:
            logger.error(f"Error executing recovery action {action}: {e}")
            return {"status": "failed", "error": str(e)}
    
    def _retry_delivery(self, order_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Attempt to retry a failed delivery"""
        if not order_id:
            return {"status": "failed", "reason": "no_order_id"}
        
        # Update order state to retry
        self.state_manager.update_order(order_id, {
            "state": OrderState.EN_ROUTE,
            # Could add retry timestamp, attempt count, etc.
        })
        
        # Notify relevant agents
        self.send_message(
            "route_planning_agent",
            "retry_delivery",
            {
                "order_id": order_id,
                "vehicle_id": vehicle_id,
                "priority": "high",
                "reason": "exception_recovery"
            }
        )
        
        return {
            "status": "initiated",
            "action": "retry_delivery",
            "order_id": order_id,
            "vehicle_id": vehicle_id
        }
    
    def _reschedule_delivery(self, order_id: str) -> Dict[str, Any]:
        """Reschedule a delivery for later"""
        if not order_id:
            return {"status": "failed", "reason": "no_order_id"}
        
        # Reschedule for next available slot (simplified)
        new_schedule_time = datetime.now() + timedelta(hours=2)
        
        self.state_manager.update_order(order_id, {
            "state": OrderState.NEW,  # Reset to allow reassignment
            "time_window_start": new_schedule_time,
            "time_window_end": new_schedule_time + timedelta(hours=1)
        })
        
        # Notify vehicle assignment agent
        self.send_message(
            "vehicle_assignment_agent",
            "order_ready_for_assignment",
            {
                "order_id": order_id,
                "priority": "normal",
                "rescheduled": True
            }
        )
        
        return {
            "status": "rescheduled",
            "action": "reschedule_delivery",
            "order_id": order_id,
            "new_schedule": new_schedule_time.isoformat()
        }
    
    def _reassign_vehicle(self, order_id: str) -> Dict[str, Any]:
        """Reassign order to a different vehicle"""
        if not order_id:
            return {"status": "failed", "reason": "no_order_id"}
        
        # Reset order state for reassignment
        self.state_manager.update_order(order_id, {
            "state": OrderState.NEW
        })
        
        # Request immediate reassignment
        self.send_message(
            "vehicle_assignment_agent",
            "urgent_reassignment",
            {
                "order_id": order_id,
                "reason": "exception_recovery",
                "priority": "urgent"
            }
        )
        
        return {
            "status": "reassignment_requested",
            "action": "reassign_vehicle",
            "order_id": order_id
        }
    
    def _dispatch_replacement_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        """Dispatch a replacement vehicle for a broken down vehicle"""
        if not vehicle_id:
            return {"status": "failed", "reason": "no_vehicle_id"}
        
        # Get the broken vehicle's assigned orders
        vehicle = self.state_manager.get_vehicle(vehicle_id)
        if not vehicle:
            return {"status": "failed", "reason": "vehicle_not_found"}
        
        # Mark vehicle as in maintenance
        self.state_manager.update_vehicle(vehicle_id, {
            "state": VehicleState.MAINTENANCE
        })
        
        # Find replacement vehicle
        available_vehicles = self.state_manager.get_available_vehicles()
        
        if available_vehicles:
            replacement_vehicle = available_vehicles[0]  # Simplified selection
            
            # Transfer orders to replacement vehicle
            self.state_manager.update_vehicle(replacement_vehicle.id, {
                "assigned_orders": vehicle.assigned_orders,
                "state": VehicleState.ASSIGNED
            })
            
            # Clear orders from broken vehicle
            self.state_manager.update_vehicle(vehicle_id, {
                "assigned_orders": []
            })
            
            # Request new route planning
            self.send_message(
                "route_planning_agent",
                "emergency_reroute",
                {
                    "vehicle_id": replacement_vehicle.id,
                    "transferred_orders": vehicle.assigned_orders,
                    "priority": "critical"
                }
            )
            
            return {
                "status": "replacement_dispatched",
                "action": "dispatch_replacement_vehicle",
                "broken_vehicle_id": vehicle_id,
                "replacement_vehicle_id": replacement_vehicle.id,
                "transferred_orders": len(vehicle.assigned_orders)
            }
        else:
            return {
                "status": "no_replacement_available",
                "action": "dispatch_replacement_vehicle",
                "broken_vehicle_id": vehicle_id
            }
    
    def _request_alternative_route(self, vehicle_id: str) -> Dict[str, Any]:
        """Request alternative route calculation"""
        self.send_message(
            "route_planning_agent",
            "calculate_alternative_route",
            {
                "vehicle_id": vehicle_id,
                "reason": "exception_recovery",
                "priority": "high"
            }
        )
        
        return {
            "status": "alternative_route_requested",
            "action": "calculate_alternative_route",
            "vehicle_id": vehicle_id
        }
    
    def _contact_customer(self, order_id: str) -> Dict[str, Any]:
        """Initiate customer contact procedure"""
        # This would integrate with customer communication systems
        return {
            "status": "customer_contact_initiated",
            "action": "contact_customer",
            "order_id": order_id,
            "contact_method": "automated_notification"
        }
    
    def _should_escalate(self, exception_record: Dict[str, Any]) -> bool:
        """Determine if an exception should be escalated"""
        exception_type = exception_record["type"]
        severity = exception_record["severity"]
        retry_count = exception_record["retry_count"]
        occurred_at = exception_record["occurred_at"]
        
        # Check escalation rules
        rules = self.escalation_rules.get(exception_type, {})
        
        # Immediate escalation for critical severity
        if severity == ExceptionSeverity.CRITICAL:
            return True
        
        # Escalation based on time
        auto_escalate_minutes = rules.get("auto_escalate_after_minutes", 30)
        if auto_escalate_minutes == 0:  # Immediate escalation
            return True
        
        time_elapsed = (datetime.now() - occurred_at).total_seconds() / 60
        if time_elapsed > auto_escalate_minutes:
            return True
        
        # Escalation based on retry attempts
        max_retries = rules.get("max_retry_attempts", 3)
        if retry_count >= max_retries:
            return True
        
        return False
    
    def _escalate_exception(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Escalate an exception to higher authority"""
        exception_id = input_data.get("exception_id")
        
        if exception_id not in self.active_exceptions:
            return {"error": "Exception not found"}
        
        exception_record = self.active_exceptions[exception_id]
        exception_record["escalation_level"] += 1
        exception_record["escalated_at"] = datetime.now()
        
        # Determine escalation target
        exception_type = exception_record["type"]
        escalation_path = self.escalation_rules.get(exception_type, {}).get("escalation_path", ["supervisor_agent"])
        escalation_level = exception_record["escalation_level"]
        
        if escalation_level <= len(escalation_path):
            target = escalation_path[escalation_level - 1]
        else:
            target = "supervisor_agent"  # Default fallback
        
        # Send escalation message
        self.send_message(
            target,
            "exception_escalation",
            {
                "exception_id": exception_id,
                "exception_record": exception_record,
                "escalation_level": escalation_level,
                "escalation_reason": "automatic_escalation"
            }
        )
        
        logger.warning(f"Exception {exception_id} escalated to {target} (level {escalation_level})")
        
        return {
            "exception_id": exception_id,
            "escalated_to": target,
            "escalation_level": escalation_level,
            "status": "escalated"
        }
    
    def _activate_emergency_protocols(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Activate emergency protocols for critical situations"""
        self.emergency_protocols_active = True
        
        critical_conflicts = input_data.get("critical_conflicts", 0)
        
        emergency_actions = []
        
        # Stop accepting new orders temporarily
        emergency_actions.append("temporarily_stop_new_orders")
        
        # Prioritize critical orders
        emergency_actions.append("prioritize_critical_orders")
        
        # Activate backup resources
        if critical_conflicts > 3:
            emergency_actions.append("activate_backup_fleet")
        
        # Notify all agents
        for agent_name in ["supervisor_agent", "vehicle_assignment_agent", "route_planning_agent"]:
            self.send_message(
                agent_name,
                "emergency_protocols_activated",
                {
                    "critical_conflicts": critical_conflicts,
                    "emergency_actions": emergency_actions,
                    "activation_time": datetime.now().isoformat()
                }
            )
        
        logger.critical(f"Emergency protocols activated due to {critical_conflicts} critical conflicts")
        
        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "emergency_protocols_active": True,
            "critical_conflicts": critical_conflicts,
            "emergency_actions": emergency_actions
        }
    
    def _review_active_exceptions(self) -> Dict[str, Any]:
        """Review all active exceptions and their status"""
        current_time = datetime.now()
        
        exception_summary = {
            "total_active": len(self.active_exceptions),
            "by_severity": {},
            "by_type": {},
            "overdue_escalations": [],
            "recent_recoveries": []
        }
        
        # Analyze active exceptions
        for exc_id, exc_record in self.active_exceptions.items():
            severity = exc_record["severity"]
            exc_type = exc_record["type"]
            
            # Count by severity
            if severity not in exception_summary["by_severity"]:
                exception_summary["by_severity"][severity] = 0
            exception_summary["by_severity"][severity] += 1
            
            # Count by type
            if exc_type not in exception_summary["by_type"]:
                exception_summary["by_type"][exc_type] = 0
            exception_summary["by_type"][exc_type] += 1
            
            # Check for overdue escalations
            if self._should_escalate(exc_record) and exc_record.get("escalation_level", 0) == 0:
                exception_summary["overdue_escalations"].append(exc_id)
        
        return {
            "agent": self.name,
            "timestamp": current_time.isoformat(),
            "exception_summary": exception_summary,
            "emergency_protocols_active": self.emergency_protocols_active
        }
    
    def _general_exception_monitoring(self) -> Dict[str, Any]:
        """General exception monitoring and maintenance"""
        current_time = datetime.now()
        
        # Check for auto-escalations
        escalations_performed = []
        for exc_id, exc_record in self.active_exceptions.items():
            if self._should_escalate(exc_record) and exc_record.get("escalation_level", 0) == 0:
                escalation_result = self._escalate_exception({"exception_id": exc_id})
                escalations_performed.append(escalation_result)
        
        # Clean up old resolved exceptions
        resolved_count = self._cleanup_resolved_exceptions()
        
        return {
            "agent": self.name,
            "timestamp": current_time.isoformat(),
            "active_exceptions": len(self.active_exceptions),
            "auto_escalations": len(escalations_performed),
            "cleaned_up_exceptions": resolved_count,
            "emergency_protocols_active": self.emergency_protocols_active
        }
    
    def _cleanup_resolved_exceptions(self) -> int:
        """Clean up old resolved exceptions"""
        cleanup_cutoff = datetime.now() - timedelta(hours=24)  # Keep for 24 hours
        
        resolved_exceptions = []
        for exc_id, exc_record in list(self.active_exceptions.items()):
            if (exc_record.get("status") == "resolved" and 
                exc_record.get("resolved_at", datetime.now()) < cleanup_cutoff):
                resolved_exceptions.append(exc_id)
                # Move to history
                self.exception_history.append(exc_record)
                del self.active_exceptions[exc_id]
        
        return len(resolved_exceptions)
    
    def _handle_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents"""
        if message.message_type == "critical_deadline":
            # Handle critical deadline violation
            return self.process({
                "action": "handle_exception",
                "exception": {
                    "type": ExceptionType.TIME_WINDOW_VIOLATION,
                    "order_id": message.payload.get("order_id"),
                    "violation_seconds": message.payload.get("violation_seconds"),
                    "description": "Critical deadline violation reported"
                }
            })
        
        elif message.message_type == "delivery_failed":
            # Handle delivery failure
            return self.process({
                "action": "handle_exception",
                "exception": {
                    "type": ExceptionType.DELIVERY_FAILURE,
                    "order_id": message.payload.get("order_id"),
                    "vehicle_id": message.payload.get("vehicle_id"),
                    "description": message.payload.get("reason", "Delivery failed")
                }
            })
        
        elif message.message_type == "vehicle_breakdown":
            # Handle vehicle breakdown
            return self.process({
                "action": "handle_exception",
                "exception": {
                    "type": ExceptionType.VEHICLE_BREAKDOWN,
                    "vehicle_id": message.payload.get("vehicle_id"),
                    "description": message.payload.get("description", "Vehicle breakdown reported")
                }
            })
        
        elif message.message_type == "emergency_activation":
            # Activate emergency protocols
            return self.process({
                "action": "emergency_activation",
                "critical_conflicts": message.payload.get("critical_conflicts", 1)
            })
        
        return super()._handle_message(message)