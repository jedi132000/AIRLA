"""
Route Planning Agent - Calculates optimal routes for vehicles and deliveries.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from base_agent import BaseAgent
from models import Vehicle, Order, Route, Location, VehicleState, AgentState


class RoutePlanningAgent(BaseAgent):
    """
    Calculates optimal routes considering traffic, time windows,
    vehicle constraints, and delivery priorities.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("route_planning_agent", state_manager, llm)
        self.routing_algorithms = ["dijkstra", "genetic_algorithm", "greedy_insertion"]
        self.current_algorithm = "greedy_insertion"
        self.calculated_routes = {}
        self.traffic_weights = {}
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process route planning requests"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            # Get current system state
            system_state = self.get_system_state()
            
            # Find vehicles needing route planning
            vehicles_needing_routes = self._get_vehicles_needing_routes(system_state)
            
            if not vehicles_needing_routes:
                logger.info("No vehicles require route planning")
                return {
                    "agent": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "message": "no_routes_needed"
                }
            
            # Plan routes for each vehicle
            route_results = []
            for vehicle in vehicles_needing_routes:
                try:
                    route_result = self._plan_vehicle_route(vehicle, system_state)
                    route_results.append(route_result)
                    logger.info(f"Route planned for vehicle {vehicle.id}")
                except Exception as e:
                    logger.error(f"Failed to plan route for vehicle {vehicle.id}: {e}")
                    route_results.append({
                        "vehicle_id": vehicle.id,
                        "status": "failed",
                        "error": str(e)
                    })
            
            # Update vehicle states and notify other agents
            self._execute_route_plans(route_results)
            
            successful_routes = [r for r in route_results if r.get("status") != "failed"]
            failed_routes = [r for r in route_results if r.get("status") == "failed"]
            
            result = {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "routes_planned": len(successful_routes),
                "routes_failed": len(failed_routes),
                "algorithm_used": self.current_algorithm,
                "successful_routes": successful_routes,
                "failed_routes": failed_routes
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Route planning agent error: {e}")
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _get_vehicles_needing_routes(self, system_state) -> List[Vehicle]:
        """Find vehicles that need route planning"""
        vehicles_needing_routes = []
        
        for vehicle in system_state.vehicles.values():
            if (vehicle.state == VehicleState.ASSIGNED and 
                vehicle.assigned_orders and
                vehicle.id not in self.calculated_routes):
                vehicles_needing_routes.append(vehicle)
        
        logger.info(f"Found {len(vehicles_needing_routes)} vehicles needing route planning")
        return vehicles_needing_routes
    
    def _plan_vehicle_route(self, vehicle: Vehicle, system_state) -> Dict[str, Any]:
        """Plan optimal route for a single vehicle"""
        # Get assigned orders
        assigned_orders = [
            system_state.orders[order_id] for order_id in vehicle.assigned_orders
            if order_id in system_state.orders
        ]
        
        if not assigned_orders:
            return {
                "vehicle_id": vehicle.id,
                "status": "no_orders",
                "message": "No valid orders assigned"
            }
        
        # Plan route based on selected algorithm
        if self.current_algorithm == "greedy_insertion":
            route_plan = self._greedy_insertion_route(vehicle, assigned_orders)
        elif self.current_algorithm == "genetic_algorithm":
            route_plan = self._genetic_algorithm_route(vehicle, assigned_orders)
        else:
            route_plan = self._simple_nearest_neighbor_route(vehicle, assigned_orders)
        
        # Calculate route metrics
        route_metrics = self._calculate_route_metrics(route_plan)
        
        # Store calculated route
        self.calculated_routes[vehicle.id] = {
            "route_plan": route_plan,
            "metrics": route_metrics,
            "calculated_at": datetime.now(),
            "vehicle_id": vehicle.id
        }
        
        return {
            "vehicle_id": vehicle.id,
            "status": "success",
            "route_plan": route_plan,
            "metrics": route_metrics,
            "algorithm": self.current_algorithm
        }
    
    def _greedy_insertion_route(self, vehicle: Vehicle, orders: List[Order]) -> List[Dict[str, Any]]:
        """Plan route using greedy insertion algorithm"""
        route_stops = []
        
        # Start from vehicle's current location
        current_location = vehicle.current_location
        remaining_orders = orders.copy()
        
        # Sort orders by priority and time constraints
        remaining_orders.sort(key=lambda x: (
            -x.priority,  # Higher priority first
            x.time_window_end.timestamp() if x.time_window_end else float('inf')
        ))
        
        current_time = datetime.now()
        
        while remaining_orders:
            best_order = None
            best_insertion_cost = float('inf')
            best_pickup_first = True
            
            for order in remaining_orders:
                # Try pickup first
                pickup_cost = self._calculate_travel_cost(
                    current_location, order.pickup_location, current_time
                )
                
                delivery_cost = self._calculate_travel_cost(
                    order.pickup_location, order.delivery_location, 
                    current_time + timedelta(minutes=pickup_cost["duration_minutes"])
                )
                
                total_cost = pickup_cost["cost"] + delivery_cost["cost"]
                
                # Consider time window constraints
                arrival_time = current_time + timedelta(minutes=pickup_cost["duration_minutes"])
                if order.time_window_start and arrival_time < order.time_window_start:
                    # Add waiting time cost
                    waiting_minutes = (order.time_window_start - arrival_time).total_seconds() / 60
                    total_cost += waiting_minutes * 0.1  # Small cost for waiting
                
                if order.time_window_end and arrival_time > order.time_window_end:
                    # Heavy penalty for late arrival
                    total_cost += 1000
                
                if total_cost < best_insertion_cost:
                    best_insertion_cost = total_cost
                    best_order = order
            
            if best_order:
                # Add pickup stop
                pickup_travel = self._calculate_travel_cost(
                    current_location, best_order.pickup_location, current_time
                )
                
                route_stops.append({
                    "type": "pickup",
                    "order_id": best_order.id,
                    "location": best_order.pickup_location,
                    "estimated_arrival": (current_time + timedelta(minutes=pickup_travel["duration_minutes"])).isoformat(),
                    "travel_distance_km": pickup_travel["distance_km"],
                    "travel_duration_minutes": pickup_travel["duration_minutes"]
                })
                
                # Update current location and time
                current_location = best_order.pickup_location
                current_time += timedelta(minutes=pickup_travel["duration_minutes"] + 5)  # 5 min pickup time
                
                # Add delivery stop
                delivery_travel = self._calculate_travel_cost(
                    current_location, best_order.delivery_location, current_time
                )
                
                route_stops.append({
                    "type": "delivery",
                    "order_id": best_order.id,
                    "location": best_order.delivery_location,
                    "estimated_arrival": (current_time + timedelta(minutes=delivery_travel["duration_minutes"])).isoformat(),
                    "travel_distance_km": delivery_travel["distance_km"],
                    "travel_duration_minutes": delivery_travel["duration_minutes"]
                })
                
                # Update for next iteration
                current_location = best_order.delivery_location
                current_time += timedelta(minutes=delivery_travel["duration_minutes"] + 3)  # 3 min delivery time
                remaining_orders.remove(best_order)
            else:
                # No feasible orders remaining
                break
        
        return route_stops
    
    def _genetic_algorithm_route(self, vehicle: Vehicle, orders: List[Order]) -> List[Dict[str, Any]]:
        """Plan route using genetic algorithm (simplified version)"""
        # This is a simplified version - full GA would be more complex
        population_size = min(20, len(orders) * 2)
        generations = 50
        
        # Generate initial population of route permutations
        import random
        population = []
        
        for _ in range(population_size):
            order_sequence = orders.copy()
            random.shuffle(order_sequence)
            population.append(order_sequence)
        
        # Evolve population
        for generation in range(generations):
            # Evaluate fitness for each individual
            fitness_scores = []
            for individual in population:
                route_stops = self._build_route_from_sequence(vehicle, individual)
                metrics = self._calculate_route_metrics(route_stops)
                # Fitness is inverse of total cost (higher fitness = lower cost)
                fitness = 1.0 / (metrics["total_distance_km"] + metrics["total_duration_minutes"] * 0.1)
                fitness_scores.append(fitness)
            
            # Selection and reproduction (simplified)
            new_population = []
            for _ in range(population_size):
                # Select two parents based on fitness
                parent1_idx = self._tournament_selection(fitness_scores)
                parent2_idx = self._tournament_selection(fitness_scores)
                
                # Crossover and mutation
                child = self._crossover(population[parent1_idx], population[parent2_idx])
                if random.random() < 0.1:  # 10% mutation rate
                    child = self._mutate(child)
                
                new_population.append(child)
            
            population = new_population
        
        # Return best individual
        best_fitness = -1
        best_individual = None
        
        for individual in population:
            route_stops = self._build_route_from_sequence(vehicle, individual)
            metrics = self._calculate_route_metrics(route_stops)
            fitness = 1.0 / (metrics["total_distance_km"] + metrics["total_duration_minutes"] * 0.1)
            
            if fitness > best_fitness:
                best_fitness = fitness
                best_individual = individual
        
        return self._build_route_from_sequence(vehicle, best_individual)
    
    def _simple_nearest_neighbor_route(self, vehicle: Vehicle, orders: List[Order]) -> List[Dict[str, Any]]:
        """Simple nearest neighbor routing algorithm"""
        route_stops = []
        current_location = vehicle.current_location
        remaining_orders = orders.copy()
        current_time = datetime.now()
        
        while remaining_orders:
            # Find nearest order
            nearest_order = None
            min_distance = float('inf')
            
            for order in remaining_orders:
                distance = self._calculate_distance(current_location, order.pickup_location)
                if distance < min_distance:
                    min_distance = distance
                    nearest_order = order
            
            if nearest_order:
                # Add pickup
                travel_cost = self._calculate_travel_cost(
                    current_location, nearest_order.pickup_location, current_time
                )
                
                route_stops.append({
                    "type": "pickup",
                    "order_id": nearest_order.id,
                    "location": nearest_order.pickup_location,
                    "estimated_arrival": (current_time + timedelta(minutes=travel_cost["duration_minutes"])).isoformat(),
                    "travel_distance_km": travel_cost["distance_km"],
                    "travel_duration_minutes": travel_cost["duration_minutes"]
                })
                
                current_location = nearest_order.pickup_location
                current_time += timedelta(minutes=travel_cost["duration_minutes"] + 5)
                
                # Add delivery
                delivery_cost = self._calculate_travel_cost(
                    current_location, nearest_order.delivery_location, current_time
                )
                
                route_stops.append({
                    "type": "delivery",
                    "order_id": nearest_order.id,
                    "location": nearest_order.delivery_location,
                    "estimated_arrival": (current_time + timedelta(minutes=delivery_cost["duration_minutes"])).isoformat(),
                    "travel_distance_km": delivery_cost["distance_km"],
                    "travel_duration_minutes": delivery_cost["duration_minutes"]
                })
                
                current_location = nearest_order.delivery_location
                current_time += timedelta(minutes=delivery_cost["duration_minutes"] + 3)
                remaining_orders.remove(nearest_order)
        
        return route_stops
    
    def _calculate_travel_cost(self, from_loc: Location, to_loc: Location, departure_time: datetime) -> Dict[str, float]:
        """Calculate travel cost between locations"""
        base_distance = self._calculate_distance(from_loc, to_loc)
        
        # Apply traffic factor based on time of day
        traffic_factor = self._get_traffic_factor(departure_time)
        
        # Base speed assumption (km/h)
        base_speed = 40.0
        adjusted_speed = base_speed * (1.0 / traffic_factor)
        
        duration_minutes = (base_distance / adjusted_speed) * 60
        
        # Cost factors
        distance_cost = base_distance * 0.5  # Cost per km
        time_cost = duration_minutes * 0.1    # Cost per minute
        
        return {
            "distance_km": base_distance,
            "duration_minutes": duration_minutes,
            "traffic_factor": traffic_factor,
            "cost": distance_cost + time_cost
        }
    
    def _get_traffic_factor(self, time: datetime) -> float:
        """Get traffic factor based on time of day"""
        hour = time.hour
        
        # Rush hour periods have higher traffic
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return 1.8  # Heavy traffic
        elif 10 <= hour <= 16:
            return 1.2  # Moderate traffic
        else:
            return 1.0  # Light traffic
    
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate distance between locations"""
        import math
        
        # Haversine formula
        lat1, lon1 = math.radians(loc1.latitude), math.radians(loc1.longitude)
        lat2, lon2 = math.radians(loc2.latitude), math.radians(loc2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Earth's radius in km
    
    def _calculate_route_metrics(self, route_stops: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate metrics for a complete route"""
        total_distance = sum(stop.get("travel_distance_km", 0) for stop in route_stops)
        total_duration = sum(stop.get("travel_duration_minutes", 0) for stop in route_stops)
        
        # Add service time estimates
        pickup_stops = [s for s in route_stops if s["type"] == "pickup"]
        delivery_stops = [s for s in route_stops if s["type"] == "delivery"]
        
        service_time = len(pickup_stops) * 5 + len(delivery_stops) * 3  # Minutes
        
        return {
            "total_distance_km": total_distance,
            "total_duration_minutes": total_duration,
            "service_time_minutes": service_time,
            "total_time_minutes": total_duration + service_time,
            "number_of_stops": len(route_stops),
            "number_of_orders": len(pickup_stops)
        }
    
    def _execute_route_plans(self, route_results: List[Dict[str, Any]]):
        """Execute route plans by updating vehicle states"""
        for route_result in route_results:
            if route_result.get("status") == "success":
                vehicle_id = route_result["vehicle_id"]
                
                # Update vehicle state to moving
                self.state_manager.update_vehicle(vehicle_id, {
                    "state": VehicleState.MOVING
                })
                
                # Store route in system
                route_id = f"route_{vehicle_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Create simplified route object for storage
                if route_result["route_plan"]:
                    first_stop = route_result["route_plan"][0]
                    last_stop = route_result["route_plan"][-1]
                    
                    route = Route(
                        start_location=Location(
                            latitude=first_stop["location"].latitude,
                            longitude=first_stop["location"].longitude
                        ),
                        end_location=Location(
                            latitude=last_stop["location"].latitude,
                            longitude=last_stop["location"].longitude
                        ),
                        distance_km=route_result["metrics"]["total_distance_km"],
                        estimated_duration_minutes=int(route_result["metrics"]["total_time_minutes"])
                    )
                    
                    self.state_manager.add_route(route_id, route)
                
                # Notify supervisor and other agents
                self._notify_route_completed(route_result)
    
    def _notify_route_completed(self, route_result: Dict[str, Any]):
        """Notify other agents about completed route planning"""
        self.send_message(
            "supervisor_agent",
            "route_planned",
            {
                "vehicle_id": route_result["vehicle_id"],
                "total_distance_km": route_result["metrics"]["total_distance_km"],
                "estimated_duration_minutes": route_result["metrics"]["total_time_minutes"],
                "number_of_stops": route_result["metrics"]["number_of_stops"]
            }
        )
        
        # Notify traffic & weather agent to monitor the route
        self.send_message(
            "traffic_weather_agent",
            "monitor_route",
            {
                "vehicle_id": route_result["vehicle_id"],
                "route_stops": route_result["route_plan"]
            }
        )
    
    # Helper methods for genetic algorithm
    def _tournament_selection(self, fitness_scores: List[float], tournament_size: int = 3) -> int:
        """Tournament selection for genetic algorithm"""
        import random
        tournament_indices = random.sample(range(len(fitness_scores)), min(tournament_size, len(fitness_scores)))
        return max(tournament_indices, key=lambda i: fitness_scores[i])
    
    def _crossover(self, parent1: List[Order], parent2: List[Order]) -> List[Order]:
        """Order crossover for genetic algorithm"""
        import random
        if len(parent1) <= 2:
            return parent1.copy()
        
        # Order crossover (OX)
        start = random.randint(0, len(parent1) - 2)
        end = random.randint(start + 1, len(parent1))
        
        child = [None] * len(parent1)
        child[start:end] = parent1[start:end]
        
        # Fill remaining positions with parent2 order
        remaining = [item for item in parent2 if item not in child]
        
        j = 0
        for i in range(len(child)):
            if child[i] is None:
                child[i] = remaining[j]
                j += 1
        
        return child
    
    def _mutate(self, individual: List[Order]) -> List[Order]:
        """Mutation for genetic algorithm"""
        import random
        mutated = individual.copy()
        
        if len(mutated) > 1:
            i, j = random.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        
        return mutated
    
    def _build_route_from_sequence(self, vehicle: Vehicle, order_sequence: List[Order]) -> List[Dict[str, Any]]:
        """Build route stops from order sequence"""
        route_stops = []
        current_location = vehicle.current_location
        current_time = datetime.now()
        
        for order in order_sequence:
            # Pickup
            travel_cost = self._calculate_travel_cost(current_location, order.pickup_location, current_time)
            
            route_stops.append({
                "type": "pickup",
                "order_id": order.id,
                "location": order.pickup_location,
                "estimated_arrival": (current_time + timedelta(minutes=travel_cost["duration_minutes"])).isoformat(),
                "travel_distance_km": travel_cost["distance_km"],
                "travel_duration_minutes": travel_cost["duration_minutes"]
            })
            
            current_location = order.pickup_location
            current_time += timedelta(minutes=travel_cost["duration_minutes"] + 5)
            
            # Delivery
            delivery_cost = self._calculate_travel_cost(current_location, order.delivery_location, current_time)
            
            route_stops.append({
                "type": "delivery",
                "order_id": order.id,
                "location": order.delivery_location,
                "estimated_arrival": (current_time + timedelta(minutes=delivery_cost["duration_minutes"])).isoformat(),
                "travel_distance_km": delivery_cost["distance_km"],
                "travel_duration_minutes": delivery_cost["duration_minutes"]
            })
            
            current_location = order.delivery_location
            current_time += timedelta(minutes=delivery_cost["duration_minutes"] + 3)
        
        return route_stops
    
    def _handle_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents"""
        if message.message_type == "new_assignment_for_routing":
            # Plan route for newly assigned vehicle
            return self.process({"specific_vehicle": message.payload.get("vehicle_id")})
        
        elif message.message_type == "optimization_suggestions":
            # Apply optimization suggestions
            suggestions = message.payload
            return self._apply_optimizations(suggestions)
        
        elif message.message_type == "traffic_update":
            # Update traffic information for route recalculation
            return self._handle_traffic_update(message.payload)
        
        return super()._handle_message(message)
    
    def _handle_traffic_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle traffic update messages"""
        # Update traffic weights and potentially recalculate routes
        location = payload.get("location")
        congestion_level = payload.get("congestion_level", 1.0)
        
        if location:
            location_key = f"{location['latitude']:.3f},{location['longitude']:.3f}"
            self.traffic_weights[location_key] = congestion_level
        
        return {
            "status": "traffic_update_processed",
            "location": location,
            "congestion_level": congestion_level
        }
    
    def _apply_optimizations(self, suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Apply optimization suggestions from supervisor"""
        optimization_results = []
        
        if suggestions.get("geographic_clustering"):
            # Implement geographic clustering
            clusters = suggestions["geographic_clustering"]
            for cluster in clusters:
                result = self._optimize_cluster(cluster)
                optimization_results.append(result)
        
        return {
            "optimizations_applied": len(optimization_results),
            "results": optimization_results
        }
    
    def _optimize_cluster(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize routes for a cluster of vehicles"""
        vehicle_ids = cluster["vehicles"]
        
        # This would implement inter-vehicle route optimization
        # For now, return a placeholder result
        return {
            "cluster_vehicles": vehicle_ids,
            "potential_savings_km": cluster.get("potential_savings", 0),
            "status": "analyzed"
        }