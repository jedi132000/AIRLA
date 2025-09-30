"""
Order Ingestion Agent - Handles incoming delivery requests and creates order nodes.
"""

from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from src.base_agent import BaseAgent
from src.models import Order, Location, AgentState, OrderState


class OrderIngestionAgent(BaseAgent):
    """
    Processes incoming delivery requests, validates data,
    and creates order nodes in the system.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("order_ingestion_agent", state_manager, llm)
        self.validation_rules = self._setup_validation_rules()
        self.processed_orders = 0
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming order requests"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            # Extract order data
            orders_data = input_data.get("orders", [])
            if isinstance(orders_data, dict):
                orders_data = [orders_data]  # Single order
            
            processed_orders = []
            failed_orders = []
            
            for order_data in orders_data:
                try:
                    # Validate order data
                    validation_result = self._validate_order_data(order_data)
                    
                    if validation_result["valid"]:
                        # Create order object
                        order = self._create_order(order_data)
                        
                        # Add to system state
                        self.state_manager.add_order(order)
                        
                        # Notify other agents
                        self._notify_new_order(order)
                        
                        processed_orders.append(order.id)
                        self.processed_orders += 1
                        
                        logger.info(f"Successfully ingested order {order.id}")
                        
                    else:
                        failed_orders.append({
                            "order_data": order_data,
                            "errors": validation_result["errors"]
                        })
                        logger.warning(f"Order validation failed: {validation_result['errors']}")
                        
                except Exception as e:
                    failed_orders.append({
                        "order_data": order_data,
                        "error": str(e)
                    })
                    logger.error(f"Error processing order: {e}")
            
            result = {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "processed_orders": len(processed_orders),
                "failed_orders": len(failed_orders),
                "order_ids": processed_orders,
                "failures": failed_orders
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Order ingestion agent error: {e}")
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _setup_validation_rules(self) -> Dict[str, Any]:
        """Setup order validation rules"""
        return {
            "required_fields": [
                "customer_id", 
                "pickup_location", 
                "delivery_location"
            ],
            "location_fields": ["latitude", "longitude"],
            "optional_fields": [
                "priority", 
                "time_window_start", 
                "time_window_end",
                "weight", 
                "volume", 
                "special_requirements"
            ],
            "max_weight_kg": 1000.0,
            "max_volume_m3": 10.0,
            "max_priority": 5
        }
    
    def _validate_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming order data"""
        validation_result = {"valid": True, "errors": []}
        
        # Check required fields
        for field in self.validation_rules["required_fields"]:
            if field not in order_data:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate locations
        for location_field in ["pickup_location", "delivery_location"]:
            if location_field in order_data:
                location_errors = self._validate_location(order_data[location_field])
                if location_errors:
                    validation_result["errors"].extend(location_errors)
                    validation_result["valid"] = False
        
        # Validate weight and volume
        if "weight" in order_data:
            if not isinstance(order_data["weight"], (int, float)) or order_data["weight"] < 0:
                validation_result["errors"].append("Weight must be a positive number")
                validation_result["valid"] = False
            elif order_data["weight"] > self.validation_rules["max_weight_kg"]:
                validation_result["errors"].append(f"Weight exceeds maximum: {self.validation_rules['max_weight_kg']}kg")
                validation_result["valid"] = False
        
        if "volume" in order_data:
            if not isinstance(order_data["volume"], (int, float)) or order_data["volume"] < 0:
                validation_result["errors"].append("Volume must be a positive number")
                validation_result["valid"] = False
            elif order_data["volume"] > self.validation_rules["max_volume_m3"]:
                validation_result["errors"].append(f"Volume exceeds maximum: {self.validation_rules['max_volume_m3']}m³")
                validation_result["valid"] = False
        
        # Validate priority
        if "priority" in order_data:
            if not isinstance(order_data["priority"], int) or not (1 <= order_data["priority"] <= self.validation_rules["max_priority"]):
                validation_result["errors"].append(f"Priority must be an integer between 1 and {self.validation_rules['max_priority']}")
                validation_result["valid"] = False
        
        # Validate time windows
        if "time_window_start" in order_data and "time_window_end" in order_data:
            try:
                start_time = datetime.fromisoformat(order_data["time_window_start"])
                end_time = datetime.fromisoformat(order_data["time_window_end"])
                
                if start_time >= end_time:
                    validation_result["errors"].append("Time window start must be before end")
                    validation_result["valid"] = False
                
                if start_time < datetime.now():
                    validation_result["errors"].append("Time window start cannot be in the past")
                    validation_result["valid"] = False
                    
            except ValueError:
                validation_result["errors"].append("Invalid time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
                validation_result["valid"] = False
        
        return validation_result
    
    def _validate_location(self, location_data: Dict[str, Any]) -> List[str]:
        """Validate location data"""
        errors = []
        
        if not isinstance(location_data, dict):
            errors.append("Location must be an object")
            return errors
        
        # Check required location fields
        for field in self.validation_rules["location_fields"]:
            if field not in location_data:
                errors.append(f"Missing location field: {field}")
            else:
                value = location_data[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"Location {field} must be a number")
                else:
                    # Validate coordinate ranges
                    if field == "latitude" and not (-90 <= value <= 90):
                        errors.append("Latitude must be between -90 and 90")
                    elif field == "longitude" and not (-180 <= value <= 180):
                        errors.append("Longitude must be between -180 and 180")
        
        return errors
    
    def _create_order(self, order_data: Dict[str, Any]) -> Order:
        """Create Order object from validated data"""
        # Generate unique order ID
        order_id = f"ORD_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.processed_orders + 1:04d}"
        
        # Create location objects
        pickup_location = Location(**order_data["pickup_location"])
        delivery_location = Location(**order_data["delivery_location"])
        
        # Parse time windows if provided
        time_window_start = None
        time_window_end = None
        
        if "time_window_start" in order_data:
            time_window_start = datetime.fromisoformat(order_data["time_window_start"])
        
        if "time_window_end" in order_data:
            time_window_end = datetime.fromisoformat(order_data["time_window_end"])
        
        # Create order
        order = Order(
            id=order_id,
            customer_id=order_data["customer_id"],
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            priority=order_data.get("priority", 1),
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            weight=order_data.get("weight", 0.0),
            volume=order_data.get("volume", 0.0),
            special_requirements=order_data.get("special_requirements", [])
        )
        
        return order
    
    def _notify_new_order(self, order: Order):
        """Notify other agents about new order"""
        # Notify supervisor
        self.send_message(
            "supervisor_agent",
            "new_order_created",
            {
                "order_id": order.id,
                "priority": order.priority,
                "customer_id": order.customer_id,
                "pickup_coords": [order.pickup_location.latitude, order.pickup_location.longitude],
                "delivery_coords": [order.delivery_location.latitude, order.delivery_location.longitude],
                "time_window": {
                    "start": order.time_window_start.isoformat() if order.time_window_start else None,
                    "end": order.time_window_end.isoformat() if order.time_window_end else None
                }
            }
        )
        
        # Notify vehicle assignment agent
        self.send_message(
            "vehicle_assignment_agent",
            "order_ready_for_assignment",
            {
                "order_id": order.id,
                "priority": order.priority,
                "location": [order.pickup_location.latitude, order.pickup_location.longitude],
                "weight": order.weight,
                "volume": order.volume
            }
        )
        
        logger.info(f"Notifications sent for new order {order.id}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get order processing statistics"""
        return {
            "total_processed": self.processed_orders,
            "agent_state": self.state_manager.get_agent_state(self.name).value,
            "last_processed": datetime.now().isoformat()
        }
    
    def _handle_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents"""
        if message.message_type == "process_orders":
            # Process new orders
            return self.process(message.payload)
        
        elif message.message_type == "validate_order":
            # Validate order without processing
            order_data = message.payload.get("order_data")
            validation_result = self._validate_order_data(order_data)
            
            return {
                "validation_result": validation_result,
                "agent": self.name
            }
        
        return super()._handle_message(message)