"""
Main logistics system orchestrator that initializes all agents and manages the workflow.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI

from state_manager import StateManager
from base_agent import AgentOrchestrator
from agents.supervisor_agent import SupervisorAgent
from agents.order_ingestion_agent import OrderIngestionAgent
from agents.vehicle_assignment_agent import VehicleAssignmentAgent
from agents.route_planning_agent import RoutePlanningAgent
from agents.traffic_weather_agent import TrafficWeatherAgent
from agents.exception_handling_agent import ExceptionHandlingAgent
from src.location_service import create_location_from_address
from src.models import Order, Vehicle, Location, OrderState, VehicleState, AgentMessage, MessageType


class LogisticsSystem:
    """
    Main logistics system that coordinates all agents and manages the overall workflow.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Load environment variables
        load_dotenv()
        
        # Initialize configuration
        self.config = config or self._load_default_config()
        
        # Initialize state manager
        self.state_manager = StateManager(
            redis_host=self.config.get("redis_host", "localhost"),
            redis_port=self.config.get("redis_port", 6379),
            redis_db=self.config.get("redis_db", 0)
        )
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=0,
            model_name=self.config.get("model_name", "gpt-3.5-turbo")
        ) if os.getenv("OPENAI_API_KEY") else None
        
        # Initialize agent orchestrator
        self.orchestrator = AgentOrchestrator(self.state_manager)
        
        # Initialize agents
        self.agents = {}
        self._initialize_agents()
        
        # System status
        self.is_running = False
        self.startup_time = None
        
        logger.info("Logistics system initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default system configuration"""
        return {
            "redis_host": os.getenv("REDIS_HOST", "localhost"),
            "redis_port": int(os.getenv("REDIS_PORT", 6379)),
            "redis_db": int(os.getenv("REDIS_DB", 0)),
            "model_name": "gpt-3.5-turbo",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "workflow_interval_seconds": 30,
            "max_concurrent_orders": 1000,
            "max_vehicles": 50
        }
    
    def _initialize_agents(self):
        """Initialize all system agents"""
        logger.info("Initializing system agents...")
        
        # Create agents
        self.agents["supervisor"] = SupervisorAgent(self.state_manager, self.llm)
        self.agents["order_ingestion"] = OrderIngestionAgent(self.state_manager, self.llm)
        self.agents["vehicle_assignment"] = VehicleAssignmentAgent(self.state_manager, self.llm)
        self.agents["route_planning"] = RoutePlanningAgent(self.state_manager, self.llm)
        self.agents["traffic_weather"] = TrafficWeatherAgent(self.state_manager, self.llm)
        self.agents["exception_handling"] = ExceptionHandlingAgent(self.state_manager, self.llm)
        
        # Register agents with orchestrator
        for agent in self.agents.values():
            self.orchestrator.register_agent(agent)
        
        # Build the workflow
        self.orchestrator.build_workflow()
        
        logger.info(f"Initialized {len(self.agents)} agents")
    
    def start_system(self):
        """Start the logistics system"""
        if self.is_running:
            logger.warning("System is already running")
            return
        
        logger.info("Starting logistics system...")
        
        try:
            # Initialize sample data if needed
            self._initialize_sample_data()
            
            # Start system
            self.is_running = True
            self.startup_time = datetime.now()
            
            logger.info("Logistics system started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start logistics system: {e}")
            self.is_running = False
            raise
    
    def stop_system(self):
        """Stop the logistics system"""
        if not self.is_running:
            logger.warning("System is not running")
            return
        
        logger.info("Stopping logistics system...")
        
        self.is_running = False
        self.startup_time = None
        
        logger.info("Logistics system stopped")
    
    def _initialize_sample_data(self):
        """Initialize system with sample vehicles and test data"""
        # Check if vehicles already exist
        system_state = self.state_manager.get_system_state()
        
        if len(system_state.vehicles) == 0:
            logger.info("Initializing sample vehicles...")
            
            # Create sample vehicles with user-friendly locations
            sample_vehicles = [
                Vehicle(
                    id="VEH_001",
                    driver_id="DRV_001",
                    vehicle_type="van",
                    capacity_weight=500.0,
                    capacity_volume=3.0,
                    current_location=create_location_from_address("Times Square, New York, NY"),
                    max_orders=8
                ),
                Vehicle(
                    id="VEH_002",
                    driver_id="DRV_002",
                    vehicle_type="truck",
                    capacity_weight=1000.0,
                    capacity_volume=8.0,
                    current_location=create_location_from_address("Central Park, New York, NY"),
                    max_orders=12
                ),
                Vehicle(
                    id="VEH_003",
                    driver_id="DRV_003",
                    vehicle_type="van",
                    capacity_weight=500.0,
                    capacity_volume=3.0,
                    current_location=create_location_from_address("Brooklyn Bridge, Brooklyn, NY"),
                    max_orders=8
                )
            ]
            
            # Add vehicles to system
            for vehicle in sample_vehicles:
                self.state_manager.add_vehicle(vehicle)
            
            logger.info(f"Added {len(sample_vehicles)} sample vehicles")
    
    def process_new_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a new order through the system"""
        if not self.is_running:
            return {"error": "System is not running"}
        
        try:
            # Send to order ingestion agent
            result = self.agents["order_ingestion"].process({"orders": [order_data]})
            
            if result.get("processed_orders", 0) > 0:
                # Trigger workflow to handle the new order
                workflow_result = self.orchestrator.run_workflow({"trigger": "new_order"})
                result["workflow_result"] = workflow_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing new order: {e}")
            return {"error": str(e)}
    
    def run_workflow_cycle(self) -> Dict[str, Any]:
        """Run one complete workflow cycle"""
        if not self.is_running:
            return {"error": "System is not running"}
        
        try:
            logger.info("Running workflow cycle...")
            
            # Run the orchestrator workflow
            workflow_result = self.orchestrator.run_workflow({"action": "process_system"})
            
            # Get system statistics
            stats = self.get_system_status()
            
            return {
                "workflow_result": workflow_result,
                "system_stats": stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in workflow cycle: {e}")
            return {"error": str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            # Get state manager stats
            stats = self.state_manager.get_system_stats()
            
            # Get agent statuses
            agent_status = self.orchestrator.get_agent_status()
            
            # Get system state
            system_state = self.state_manager.get_system_state()
            
            # Calculate additional metrics
            if system_state.orders:
                order_states = {}
                for order in system_state.orders.values():
                    state = order.state.value
                    order_states[state] = order_states.get(state, 0) + 1
            else:
                order_states = {}
            
            if system_state.vehicles:
                vehicle_states = {}
                for vehicle in system_state.vehicles.values():
                    state = vehicle.state.value
                    vehicle_states[state] = vehicle_states.get(state, 0) + 1
            else:
                vehicle_states = {}
            
            return {
                "system_running": self.is_running,
                "startup_time": self.startup_time.isoformat() if self.startup_time else None,
                "uptime_minutes": (datetime.now() - self.startup_time).total_seconds() / 60 if self.startup_time else 0,
                "total_agents": len(self.agents),
                "agent_status": agent_status,
                "storage_stats": stats,
                "order_states": order_states,
                "vehicle_states": vehicle_states,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
    
    def get_orders(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of orders"""
        try:
            system_state = self.state_manager.get_system_state()
            
            orders_list = []
            for order in list(system_state.orders.values())[:limit]:
                orders_list.append({
                    "id": order.id,
                    "customer_id": order.customer_id,
                    "state": order.state.value,
                    "priority": order.priority,
                    "created_at": order.created_at.isoformat(),
                    "pickup_location": {
                        "latitude": order.pickup_location.latitude,
                        "longitude": order.pickup_location.longitude,
                        "address": order.pickup_location.address
                    },
                    "delivery_location": {
                        "latitude": order.delivery_location.latitude,
                        "longitude": order.delivery_location.longitude,
                        "address": order.delivery_location.address
                    },
                    "weight": order.weight,
                    "volume": order.volume
                })
            
            return orders_list
            
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def get_vehicles(self) -> List[Dict[str, Any]]:
        """Get list of vehicles"""
        try:
            system_state = self.state_manager.get_system_state()
            
            vehicles_list = []
            for vehicle in system_state.vehicles.values():
                vehicles_list.append({
                    "id": vehicle.id,
                    "driver_id": vehicle.driver_id,
                    "vehicle_type": vehicle.vehicle_type,
                    "state": vehicle.state.value,
                    "current_location": {
                        "latitude": vehicle.current_location.latitude,
                        "longitude": vehicle.current_location.longitude
                    },
                    "capacity_weight": vehicle.capacity_weight,
                    "capacity_volume": vehicle.capacity_volume,
                    "assigned_orders": vehicle.assigned_orders,
                    "max_orders": vehicle.max_orders
                })
            
            return vehicles_list
            
        except Exception as e:
            logger.error(f"Error getting vehicles: {e}")
            return []
    
    def trigger_emergency_protocols(self, reason: str = "manual_trigger") -> Dict[str, Any]:
        """Trigger emergency protocols"""
        try:
            result = self.agents["exception_handling"].process({
                "action": "emergency_activation",
                "critical_conflicts": 5,  # Simulate high conflict count
                "reason": reason
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error triggering emergency protocols: {e}")
            return {"error": str(e)}
    
    def simulate_delivery_failure(self, order_id: str, reason: str = "customer_unavailable") -> Dict[str, Any]:
        """Simulate a delivery failure for testing"""
        try:
            result = self.agents["exception_handling"].process({
                "action": "handle_exception",
                "exception": {
                    "type": "delivery_failure",
                    "order_id": order_id,
                    "description": f"Simulated delivery failure: {reason}"
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error simulating delivery failure: {e}")
            return {"error": str(e)}
    
    def clear_system_data(self, confirm: bool = False) -> Dict[str, Any]:
        """Clear all system data (use with caution!)"""
        if not confirm:
            return {"error": "Must set confirm=True to clear data"}
        
        try:
            self.state_manager.clear_all_data()
            
            # Reinitialize sample data
            self._initialize_sample_data()
            
            return {
                "status": "success",
                "message": "System data cleared and reinitialized",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error clearing system data: {e}")
            return {"error": str(e)}