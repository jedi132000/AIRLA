"""
State management system using Redis for real-time updates.
Handles persistence and synchronization of system state.
"""

import redis
from typing import Dict, List, Optional, Any
from loguru import logger

from models import SystemState, Order, Vehicle, Route, AgentState


class StateManager:
    """Centralized state management with Redis backend"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            decode_responses=True
        )
        self.state_key = "logistics:system_state"
        self.orders_key = "logistics:orders"
        self.vehicles_key = "logistics:vehicles"
        self.routes_key = "logistics:routes"
        self.agents_key = "logistics:agents"
        
        # Initialize system state if not exists
        self._initialize_state()
    
    def _initialize_state(self):
        """Initialize system state in Redis if it doesn't exist"""
        if not self.redis_client.exists(self.state_key):
            initial_state = SystemState()
            self.save_system_state(initial_state)
            logger.info("Initialized new system state in Redis")
    
    def get_system_state(self) -> SystemState:
        """Retrieve complete system state from Redis"""
        try:
            state_data = self.redis_client.get(self.state_key)
            if state_data:
                return SystemState.parse_raw(state_data)
            else:
                return SystemState()
        except Exception as e:
            logger.error(f"Error retrieving system state: {e}")
            return SystemState()
    
    def save_system_state(self, state: SystemState):
        """Save complete system state to Redis"""
        try:
            state.update_timestamp()
            self.redis_client.set(self.state_key, state.json())
            logger.debug("System state saved to Redis")
        except Exception as e:
            logger.error(f"Error saving system state: {e}")
    
    def add_order(self, order: Order):
        """Add new order to system"""
        try:
            # Add to orders hash
            self.redis_client.hset(self.orders_key, order.id, order.json())
            
            # Update system state
            state = self.get_system_state()
            state.orders[order.id] = order
            self.save_system_state(state)
            
            logger.info(f"Added order {order.id} to system")
        except Exception as e:
            logger.error(f"Error adding order {order.id}: {e}")
    
    def update_order(self, order_id: str, updates: Dict[str, Any]):
        """Update specific order fields"""
        try:
            order_data = self.redis_client.hget(self.orders_key, order_id)
            if order_data:
                order = Order.parse_raw(order_data)
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(order, field):
                        setattr(order, field, value)
                
                # Save back
                self.redis_client.hset(self.orders_key, order_id, order.json())
                
                # Update system state
                state = self.get_system_state()
                state.orders[order_id] = order
                self.save_system_state(state)
                
                logger.info(f"Updated order {order_id}")
            else:
                logger.warning(f"Order {order_id} not found for update")
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get specific order by ID"""
        try:
            order_data = self.redis_client.hget(self.orders_key, order_id)
            return Order.parse_raw(order_data) if order_data else None
        except Exception as e:
            logger.error(f"Error retrieving order {order_id}: {e}")
            return None
    
    def add_vehicle(self, vehicle: Vehicle):
        """Add new vehicle to system"""
        try:
            self.redis_client.hset(self.vehicles_key, vehicle.id, vehicle.json())
            
            # Update system state
            state = self.get_system_state()
            state.vehicles[vehicle.id] = vehicle
            self.save_system_state(state)
            
            logger.info(f"Added vehicle {vehicle.id} to system")
        except Exception as e:
            logger.error(f"Error adding vehicle {vehicle.id}: {e}")
    
    def update_vehicle(self, vehicle_id: str, updates: Dict[str, Any]):
        """Update specific vehicle fields"""
        try:
            vehicle_data = self.redis_client.hget(self.vehicles_key, vehicle_id)
            if vehicle_data:
                vehicle = Vehicle.parse_raw(vehicle_data)
                
                # Apply updates
                for field, value in updates.items():
                    if hasattr(vehicle, field):
                        setattr(vehicle, field, value)
                
                # Save back
                self.redis_client.hset(self.vehicles_key, vehicle_id, vehicle.json())
                
                # Update system state
                state = self.get_system_state()
                state.vehicles[vehicle_id] = vehicle
                self.save_system_state(state)
                
                logger.info(f"Updated vehicle {vehicle_id}")
            else:
                logger.warning(f"Vehicle {vehicle_id} not found for update")
        except Exception as e:
            logger.error(f"Error updating vehicle {vehicle_id}: {e}")
    
    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Get specific vehicle by ID"""
        try:
            vehicle_data = self.redis_client.hget(self.vehicles_key, vehicle_id)
            return Vehicle.parse_raw(vehicle_data) if vehicle_data else None
        except Exception as e:
            logger.error(f"Error retrieving vehicle {vehicle_id}: {e}")
            return None
    
    def get_available_vehicles(self) -> List[Vehicle]:
        """Get all vehicles that are idle or available for assignment"""
        try:
            vehicles = []
            vehicle_ids = self.redis_client.hkeys(self.vehicles_key)
            
            for vehicle_id in vehicle_ids:
                vehicle = self.get_vehicle(vehicle_id)
                if vehicle and vehicle.state in ["idle", "assigned"]:
                    vehicles.append(vehicle)
            
            return vehicles
        except Exception as e:
            logger.error(f"Error retrieving available vehicles: {e}")
            return []
    
    def update_agent_state(self, agent_name: str, state: AgentState):
        """Update agent state"""
        try:
            self.redis_client.hset(self.agents_key, agent_name, state.value)
            
            # Update system state
            system_state = self.get_system_state()
            system_state.agent_states[agent_name] = state
            self.save_system_state(system_state)
            
            logger.debug(f"Updated agent {agent_name} state to {state.value}")
        except Exception as e:
            logger.error(f"Error updating agent {agent_name} state: {e}")
    
    def get_agent_state(self, agent_name: str) -> Optional[AgentState]:
        """Get current agent state"""
        try:
            state_value = self.redis_client.hget(self.agents_key, agent_name)
            return AgentState(state_value) if state_value else None
        except Exception as e:
            logger.error(f"Error retrieving agent {agent_name} state: {e}")
            return None
    
    def add_route(self, route_id: str, route: Route):
        """Add calculated route to system"""
        try:
            self.redis_client.hset(self.routes_key, route_id, route.json())
            
            # Update system state
            state = self.get_system_state()
            state.routes[route_id] = route
            self.save_system_state(state)
            
            logger.info(f"Added route {route_id} to system")
        except Exception as e:
            logger.error(f"Error adding route {route_id}: {e}")
    
    def clear_all_data(self):
        """Clear all system data - use with caution!"""
        try:
            self.redis_client.delete(
                self.state_key,
                self.orders_key, 
                self.vehicles_key,
                self.routes_key,
                self.agents_key
            )
            self._initialize_state()
            logger.info("Cleared all system data and reinitialized")
        except Exception as e:
            logger.error(f"Error clearing system data: {e}")
    
    def get_system_stats(self) -> Dict[str, int]:
        """Get system statistics"""
        try:
            stats = {
                "total_orders": self.redis_client.hlen(self.orders_key),
                "total_vehicles": self.redis_client.hlen(self.vehicles_key),
                "total_routes": self.redis_client.hlen(self.routes_key),
                "active_agents": self.redis_client.hlen(self.agents_key)
            }
            return stats
        except Exception as e:
            logger.error(f"Error retrieving system stats: {e}")
            return {}