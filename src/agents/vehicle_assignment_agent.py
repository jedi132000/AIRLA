"""
Vehicle Assignment Agent - Assigns vehicles to delivery tasks based on capacity, location, and operational limits.
"""

import math
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from base_agent import BaseAgent
from models import Vehicle, Order, VehicleState, OrderState, AgentState, Location


class VehicleAssignmentAgent(BaseAgent):
    """
    Assigns vehicles to delivery orders based on optimization criteria
    including distance, capacity, availability, and constraints.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("vehicle_assignment_agent", state_manager, llm)
        self.assignment_algorithms = ["nearest_vehicle", "capacity_optimized", "balanced_workload"]
        self.current_algorithm = "balanced_workload"
        self.assignment_history = []
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process vehicle assignment requests"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            # Get current system state
            system_state = self.get_system_state()
            
            # Find orders needing assignment
            unassigned_orders = [
                order for order in system_state.orders.values() 
                if order.state == OrderState.NEW
            ]
            
            # Find available vehicles
            available_vehicles = self._get_available_vehicles(system_state)
            
            if not unassigned_orders:
                logger.info("No orders requiring assignment")
                return {
                    "agent": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "message": "no_orders_to_assign"
                }
            
            if not available_vehicles:
                logger.warning("No vehicles available for assignment")
                return {
                    "agent": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "message": "no_vehicles_available",
                    "unassigned_orders": len(unassigned_orders)
                }
            
            # Perform assignments
            assignments = self._assign_vehicles_to_orders(unassigned_orders, available_vehicles)
            
            # Execute assignments
            execution_results = self._execute_assignments(assignments)
            
            result = {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "assignments_made": len(execution_results["successful"]),
                "assignments_failed": len(execution_results["failed"]),
                "algorithm_used": self.current_algorithm,
                "successful_assignments": execution_results["successful"],
                "failed_assignments": execution_results["failed"]
            }
            
            logger.info(f"Vehicle assignment completed: {len(execution_results['successful'])} successful assignments")
            return result
            
        except Exception as e:
            logger.error(f"Vehicle assignment agent error: {e}")
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _get_available_vehicles(self, system_state) -> List[Vehicle]:
        """Get list of available vehicles for assignment"""
        available_vehicles = []
        
        for vehicle in system_state.vehicles.values():
            if vehicle.state == VehicleState.IDLE:
                available_vehicles.append(vehicle)
            elif (vehicle.state == VehicleState.ASSIGNED and 
                  len(vehicle.assigned_orders) < vehicle.max_orders):
                # Vehicle can take more orders
                available_vehicles.append(vehicle)
        
        logger.info(f"Found {len(available_vehicles)} available vehicles")
        return available_vehicles
    
    def _assign_vehicles_to_orders(self, orders: List[Order], vehicles: List[Vehicle]) -> List[Dict[str, Any]]:
        """Assign vehicles to orders using the selected algorithm"""
        assignments = []
        
        if self.current_algorithm == "nearest_vehicle":
            assignments = self._nearest_vehicle_assignment(orders, vehicles)
        elif self.current_algorithm == "capacity_optimized":
            assignments = self._capacity_optimized_assignment(orders, vehicles)
        elif self.current_algorithm == "balanced_workload":
            assignments = self._balanced_workload_assignment(orders, vehicles)
        
        return assignments
    
    def _nearest_vehicle_assignment(self, orders: List[Order], vehicles: List[Vehicle]) -> List[Dict[str, Any]]:
        """Assign orders to nearest available vehicles"""
        assignments = []
        available_vehicles = vehicles.copy()
        
        # Sort orders by priority (high priority first)
        sorted_orders = sorted(orders, key=lambda x: x.priority, reverse=True)
        
        for order in sorted_orders:
            if not available_vehicles:
                break
            
            best_vehicle = None
            min_distance = float('inf')
            
            for vehicle in available_vehicles:
                # Check capacity constraints
                if not self._check_capacity_constraints(vehicle, order):
                    continue
                
                # Calculate distance from vehicle to pickup location
                distance = self._calculate_distance(
                    vehicle.current_location,
                    order.pickup_location
                )
                
                if distance < min_distance:
                    min_distance = distance
                    best_vehicle = vehicle
            
            if best_vehicle:
                assignments.append({
                    "order_id": order.id,
                    "vehicle_id": best_vehicle.id,
                    "distance_km": min_distance,
                    "algorithm": "nearest_vehicle"
                })
                
                # Remove vehicle if it reaches capacity
                if len(best_vehicle.assigned_orders) + 1 >= best_vehicle.max_orders:
                    available_vehicles.remove(best_vehicle)
        
        return assignments
    
    def _capacity_optimized_assignment(self, orders: List[Order], vehicles: List[Vehicle]) -> List[Dict[str, Any]]:
        """Assign orders to optimize vehicle capacity utilization"""
        assignments = []
        
        # Group orders by size categories
        small_orders = [o for o in orders if o.weight <= 10 and o.volume <= 0.5]
        medium_orders = [o for o in orders if 10 < o.weight <= 50 and 0.5 < o.volume <= 2.0]
        large_orders = [o for o in orders if o.weight > 50 or o.volume > 2.0]
        
        # Assign large orders first
        for order_group in [large_orders, medium_orders, small_orders]:
            for order in sorted(order_group, key=lambda x: x.priority, reverse=True):
                best_vehicle = self._find_best_capacity_match(order, vehicles)
                
                if best_vehicle:
                    distance = self._calculate_distance(
                        best_vehicle.current_location,
                        order.pickup_location
                    )
                    
                    assignments.append({
                        "order_id": order.id,
                        "vehicle_id": best_vehicle.id,
                        "distance_km": distance,
                        "algorithm": "capacity_optimized"
                    })
        
        return assignments
    
    def _balanced_workload_assignment(self, orders: List[Order], vehicles: List[Vehicle]) -> List[Dict[str, Any]]:
        """Assign orders to balance workload across vehicles"""
        assignments = []
        
        # Sort orders by priority
        sorted_orders = sorted(orders, key=lambda x: x.priority, reverse=True)
        
        for order in sorted_orders:
            # Find vehicle with best balance of distance and current workload
            best_vehicle = self._find_balanced_vehicle(order, vehicles)
            
            if best_vehicle:
                distance = self._calculate_distance(
                    best_vehicle.current_location,
                    order.pickup_location
                )
                
                assignments.append({
                    "order_id": order.id,
                    "vehicle_id": best_vehicle.id,
                    "distance_km": distance,
                    "workload_score": len(best_vehicle.assigned_orders),
                    "algorithm": "balanced_workload"
                })
        
        return assignments
    
    def _find_best_capacity_match(self, order: Order, vehicles: List[Vehicle]) -> Optional[Vehicle]:
        """Find vehicle with best capacity match for the order"""
        suitable_vehicles = []
        
        for vehicle in vehicles:
            if self._check_capacity_constraints(vehicle, order):
                # Calculate remaining capacity after assignment
                remaining_weight = vehicle.capacity_weight - self._calculate_current_weight(vehicle) - order.weight
                remaining_volume = vehicle.capacity_volume - self._calculate_current_volume(vehicle) - order.volume
                
                # Prefer vehicles that will be efficiently utilized
                utilization_score = 1.0 - min(
                    remaining_weight / vehicle.capacity_weight,
                    remaining_volume / vehicle.capacity_volume
                )
                
                suitable_vehicles.append((vehicle, utilization_score))
        
        if suitable_vehicles:
            # Return vehicle with highest utilization score
            return max(suitable_vehicles, key=lambda x: x[1])[0]
        
        return None
    
    def _find_balanced_vehicle(self, order: Order, vehicles: List[Vehicle]) -> Optional[Vehicle]:
        """Find vehicle that provides best balance of distance and workload"""
        best_vehicle = None
        best_score = float('inf')
        
        for vehicle in vehicles:
            if not self._check_capacity_constraints(vehicle, order):
                continue
            
            # Calculate distance score (normalized)
            distance = self._calculate_distance(vehicle.current_location, order.pickup_location)
            distance_score = distance / 50.0  # Normalize by 50km
            
            # Calculate workload score (normalized)
            workload_score = len(vehicle.assigned_orders) / vehicle.max_orders
            
            # Combined score (weighted)
            combined_score = (0.6 * distance_score) + (0.4 * workload_score)
            
            if combined_score < best_score:
                best_score = combined_score
                best_vehicle = vehicle
        
        return best_vehicle
    
    def _check_capacity_constraints(self, vehicle: Vehicle, order: Order) -> bool:
        """Check if vehicle can accommodate the order"""
        # Check order count
        if len(vehicle.assigned_orders) >= vehicle.max_orders:
            return False
        
        # Check weight capacity
        current_weight = self._calculate_current_weight(vehicle)
        if current_weight + order.weight > vehicle.capacity_weight:
            return False
        
        # Check volume capacity
        current_volume = self._calculate_current_volume(vehicle)
        if current_volume + order.volume > vehicle.capacity_volume:
            return False
        
        return True
    
    def _calculate_current_weight(self, vehicle: Vehicle) -> float:
        """Calculate current weight load of vehicle"""
        # This would typically query assigned orders and sum their weights
        # For now, return estimated weight based on number of orders
        return len(vehicle.assigned_orders) * 15.0  # Assume 15kg average per order
    
    def _calculate_current_volume(self, vehicle: Vehicle) -> float:
        """Calculate current volume load of vehicle"""
        # This would typically query assigned orders and sum their volumes
        # For now, return estimated volume based on number of orders
        return len(vehicle.assigned_orders) * 0.3  # Assume 0.3m³ average per order
    
    def _calculate_distance(self, location1: Location, location2: Location) -> float:
        """Calculate distance between two locations using Haversine formula"""
        # Convert latitude and longitude from degrees to radians
        lat1, lon1 = math.radians(location1.latitude), math.radians(location1.longitude)
        lat2, lon2 = math.radians(location2.latitude), math.radians(location2.longitude)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        
        return r * c
    
    def _execute_assignments(self, assignments: List[Dict[str, Any]]) -> Dict[str, List]:
        """Execute the vehicle assignments"""
        execution_results = {
            "successful": [],
            "failed": []
        }
        
        for assignment in assignments:
            try:
                order_id = assignment["order_id"]
                vehicle_id = assignment["vehicle_id"]
                
                # Update order state
                self.state_manager.update_order(order_id, {"state": OrderState.ASSIGNED})
                
                # Update vehicle assignment
                vehicle = self.state_manager.get_vehicle(vehicle_id)
                if vehicle:
                    updated_orders = vehicle.assigned_orders.copy()
                    updated_orders.append(order_id)
                    
                    self.state_manager.update_vehicle(vehicle_id, {
                        "assigned_orders": updated_orders,
                        "state": VehicleState.ASSIGNED
                    })
                
                # Record assignment
                assignment_record = {
                    **assignment,
                    "timestamp": datetime.now().isoformat(),
                    "status": "successful"
                }
                
                self.assignment_history.append(assignment_record)
                execution_results["successful"].append(assignment_record)
                
                # Notify other agents
                self._notify_assignment_completed(assignment)
                
                logger.info(f"Successfully assigned order {order_id} to vehicle {vehicle_id}")
                
            except Exception as e:
                assignment_record = {
                    **assignment,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                }
                
                execution_results["failed"].append(assignment_record)
                logger.error(f"Failed to execute assignment for order {assignment['order_id']}: {e}")
        
        return execution_results
    
    def _notify_assignment_completed(self, assignment: Dict[str, Any]):
        """Notify other agents about completed assignment"""
        # Notify supervisor
        self.send_message(
            "supervisor_agent",
            "assignment_completed",
            {
                "order_id": assignment["order_id"],
                "vehicle_id": assignment["vehicle_id"],
                "distance_km": assignment["distance_km"],
                "algorithm": assignment["algorithm"]
            }
        )
        
        # Notify route planning agent
        self.send_message(
            "route_planning_agent",
            "new_assignment_for_routing",
            {
                "order_id": assignment["order_id"],
                "vehicle_id": assignment["vehicle_id"],
                "pickup_required": True,
                "priority": "normal"
            }
        )
    
    def rebalance_vehicle(self, vehicle_id: str) -> Dict[str, Any]:
        """Rebalance assignments for an overloaded vehicle"""
        try:
            vehicle = self.state_manager.get_vehicle(vehicle_id)
            if not vehicle:
                return {"error": f"Vehicle {vehicle_id} not found"}
            
            if len(vehicle.assigned_orders) <= vehicle.max_orders:
                return {"message": "Vehicle not overloaded"}
            
            # Find orders to reassign (lowest priority first)
            system_state = self.get_system_state()
            assigned_orders = [
                system_state.orders[order_id] for order_id in vehicle.assigned_orders 
                if order_id in system_state.orders
            ]
            
            # Sort by priority (lowest first) and take excess orders
            excess_count = len(vehicle.assigned_orders) - vehicle.max_orders
            orders_to_reassign = sorted(assigned_orders, key=lambda x: x.priority)[:excess_count]
            
            # Find alternative vehicles
            available_vehicles = self._get_available_vehicles(system_state)
            available_vehicles = [v for v in available_vehicles if v.id != vehicle_id]
            
            reassignments = []
            for order in orders_to_reassign:
                best_vehicle = self._find_balanced_vehicle(order, available_vehicles)
                if best_vehicle:
                    # Remove from current vehicle
                    updated_orders = [o for o in vehicle.assigned_orders if o != order.id]
                    self.state_manager.update_vehicle(vehicle_id, {"assigned_orders": updated_orders})
                    
                    # Assign to new vehicle
                    new_vehicle_orders = best_vehicle.assigned_orders.copy()
                    new_vehicle_orders.append(order.id)
                    self.state_manager.update_vehicle(best_vehicle.id, {
                        "assigned_orders": new_vehicle_orders,
                        "state": VehicleState.ASSIGNED
                    })
                    
                    reassignments.append({
                        "order_id": order.id,
                        "from_vehicle": vehicle_id,
                        "to_vehicle": best_vehicle.id
                    })
            
            logger.info(f"Rebalanced vehicle {vehicle_id}: {len(reassignments)} orders reassigned")
            return {
                "vehicle_id": vehicle_id,
                "reassignments": len(reassignments),
                "details": reassignments
            }
            
        except Exception as e:
            logger.error(f"Error rebalancing vehicle {vehicle_id}: {e}")
            return {"error": str(e)}
    
    def _handle_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents"""
        if message.message_type == "order_ready_for_assignment":
            # Process single order assignment
            order_id = message.payload.get("order_id")
            return self.process({"specific_order": order_id})
        
        elif message.message_type == "rebalance_vehicle":
            # Rebalance overloaded vehicle
            vehicle_id = message.payload.get("vehicle_id")
            return self.rebalance_vehicle(vehicle_id)
        
        elif message.message_type == "change_algorithm":
            # Change assignment algorithm
            new_algorithm = message.payload.get("algorithm")
            if new_algorithm in self.assignment_algorithms:
                self.current_algorithm = new_algorithm
                return {"algorithm_changed": new_algorithm}
        
        return super()._handle_message(message)