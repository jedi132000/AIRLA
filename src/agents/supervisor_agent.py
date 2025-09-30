"""
Supervisor Agent - Oversees all other agents and coordinates the global workflow.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from base_agent import BaseAgent
from models import AgentState, OrderState, VehicleState


class SupervisorAgent(BaseAgent):
    """
    The Supervisor Agent manages overall system coordination,
    resolves conflicts, and optimizes global routing decisions.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("supervisor_agent", state_manager, llm)
        self.conflict_resolution_rules = []
        self.performance_metrics = {}
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main supervisor processing logic"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            # Get current system state
            system_state = self.get_system_state()
            
            # Perform global analysis
            analysis = self._analyze_system_performance(system_state)
            
            # Detect and resolve conflicts
            conflicts = self._detect_conflicts(system_state)
            resolutions = self._resolve_conflicts(conflicts)
            
            # Optimize global routes
            optimization_recommendations = self._optimize_global_routes(system_state)
            
            # Make strategic decisions
            decisions = self._make_strategic_decisions(analysis, conflicts, optimization_recommendations)
            
            # Execute decisions
            execution_results = self._execute_decisions(decisions)
            
            result = {
                "agent": self.name,
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "conflicts_resolved": len(resolutions),
                "optimization_recommendations": optimization_recommendations,
                "decisions": decisions,
                "execution_results": execution_results
            }
            
            logger.info(f"Supervisor completed processing: {len(decisions)} decisions made")
            return result
            
        except Exception as e:
            logger.error(f"Supervisor agent error: {e}")
            self.update_state(AgentState.MONITORING)
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _analyze_system_performance(self, system_state) -> Dict[str, Any]:
        """Analyze overall system performance metrics"""
        analysis = {
            "total_orders": len(system_state.orders),
            "total_vehicles": len(system_state.vehicles),
            "delivery_efficiency": 0.0,
            "resource_utilization": 0.0,
            "bottlenecks": []
        }
        
        if system_state.orders:
            # Calculate delivery efficiency
            completed_orders = [o for o in system_state.orders.values() 
                             if o.state == OrderState.DELIVERED]
            analysis["delivery_efficiency"] = len(completed_orders) / len(system_state.orders)
            
            # Identify bottlenecks
            failed_orders = [o for o in system_state.orders.values() 
                           if o.state == OrderState.FAILED]
            if len(failed_orders) > len(system_state.orders) * 0.1:  # >10% failure rate
                analysis["bottlenecks"].append("high_failure_rate")
        
        if system_state.vehicles:
            # Calculate resource utilization
            active_vehicles = [v for v in system_state.vehicles.values() 
                             if v.state in [VehicleState.ASSIGNED, VehicleState.MOVING]]
            analysis["resource_utilization"] = len(active_vehicles) / len(system_state.vehicles)
        
        # Store metrics for historical analysis
        self.performance_metrics[datetime.now().isoformat()] = analysis
        
        return analysis
    
    def _detect_conflicts(self, system_state) -> List[Dict[str, Any]]:
        """Detect conflicts in the system that need resolution"""
        conflicts = []
        
        # Check for vehicle assignment conflicts
        vehicle_assignments = {}
        for order in system_state.orders.values():
            if order.state == OrderState.ASSIGNED:
                # Find assigned vehicle (this would need vehicle->order mapping)
                for vehicle in system_state.vehicles.values():
                    if order.id in vehicle.assigned_orders:
                        if vehicle.id not in vehicle_assignments:
                            vehicle_assignments[vehicle.id] = []
                        vehicle_assignments[vehicle.id].append(order.id)
        
        # Detect overloaded vehicles
        for vehicle_id, assigned_orders in vehicle_assignments.items():
            vehicle = system_state.vehicles[vehicle_id]
            if len(assigned_orders) > vehicle.max_orders:
                conflicts.append({
                    "type": "vehicle_overload",
                    "vehicle_id": vehicle_id,
                    "assigned_orders": len(assigned_orders),
                    "max_capacity": vehicle.max_orders,
                    "severity": "high"
                })
        
        # Check for time window conflicts
        current_time = datetime.now()
        for order in system_state.orders.values():
            if (order.time_window_end and 
                current_time > order.time_window_end and 
                order.state not in [OrderState.DELIVERED, OrderState.FAILED]):
                conflicts.append({
                    "type": "time_window_violation",
                    "order_id": order.id,
                    "deadline_passed": (current_time - order.time_window_end).total_seconds(),
                    "severity": "critical"
                })
        
        logger.info(f"Detected {len(conflicts)} system conflicts")
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve detected conflicts"""
        resolutions = []
        
        for conflict in conflicts:
            resolution = None
            
            if conflict["type"] == "vehicle_overload":
                # Reassign some orders to other vehicles
                resolution = self._resolve_vehicle_overload(conflict)
            
            elif conflict["type"] == "time_window_violation":
                # Prioritize or escalate critical orders
                resolution = self._resolve_time_window_violation(conflict)
            
            if resolution:
                resolutions.append(resolution)
                logger.info(f"Resolved conflict: {conflict['type']}")
        
        return resolutions
    
    def _resolve_vehicle_overload(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve vehicle overload by reassigning orders"""
        vehicle_id = conflict["vehicle_id"]
        
        # Send message to vehicle assignment agent to rebalance
        self.send_message(
            "vehicle_assignment_agent",
            "rebalance_vehicle",
            {
                "vehicle_id": vehicle_id,
                "reason": "overload",
                "priority": "high"
            }
        )
        
        return {
            "conflict_type": "vehicle_overload",
            "action": "reassignment_requested",
            "vehicle_id": vehicle_id
        }
    
    def _resolve_time_window_violation(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve time window violations"""
        order_id = conflict["order_id"]
        
        # Escalate to exception handling
        self.send_message(
            "exception_handling_agent",
            "critical_deadline",
            {
                "order_id": order_id,
                "violation_seconds": conflict["deadline_passed"],
                "priority": "critical"
            }
        )
        
        return {
            "conflict_type": "time_window_violation", 
            "action": "escalated_to_exception_handler",
            "order_id": order_id
        }
    
    def _optimize_global_routes(self, system_state) -> Dict[str, Any]:
        """Provide global route optimization recommendations"""
        recommendations = {
            "route_consolidation": [],
            "capacity_optimization": [],
            "geographic_clustering": []
        }
        
        # Analyze current routes for optimization opportunities
        active_vehicles = [v for v in system_state.vehicles.values() 
                          if v.state in [VehicleState.ASSIGNED, VehicleState.MOVING]]
        
        if len(active_vehicles) > 1:
            # Look for geographic clustering opportunities
            recommendations["geographic_clustering"] = self._find_clustering_opportunities(active_vehicles)
        
        # Send optimization suggestions to route planning agent
        if any(recommendations.values()):
            self.send_message(
                "route_planning_agent",
                "optimization_suggestions",
                recommendations
            )
        
        return recommendations
    
    def _find_clustering_opportunities(self, vehicles: List) -> List[Dict[str, Any]]:
        """Find opportunities to cluster nearby deliveries"""
        opportunities = []
        
        # Simplified clustering based on vehicle proximity
        for i, vehicle_a in enumerate(vehicles):
            for j, vehicle_b in enumerate(vehicles[i+1:], i+1):
                # Check if vehicles are operating in similar areas
                distance = self._calculate_distance(
                    vehicle_a.current_location,
                    vehicle_b.current_location
                )
                
                if distance < 5.0:  # Within 5km
                    opportunities.append({
                        "vehicles": [vehicle_a.id, vehicle_b.id],
                        "distance_km": distance,
                        "potential_savings": distance * 0.5  # Estimate
                    })
        
        return opportunities
    
    def _calculate_distance(self, loc1, loc2) -> float:
        """Simple distance calculation (would use proper geospatial library)"""
        # Simplified Euclidean distance
        lat_diff = abs(loc1.latitude - loc2.latitude)
        lng_diff = abs(loc1.longitude - loc2.longitude)
        return ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Rough km conversion
    
    def _make_strategic_decisions(self, analysis: Dict, conflicts: List, optimizations: Dict) -> List[Dict[str, Any]]:
        """Make high-level strategic decisions"""
        decisions = []
        
        # Decision based on delivery efficiency
        if analysis["delivery_efficiency"] < 0.8:  # Less than 80% efficiency
            decisions.append({
                "type": "efficiency_improvement",
                "action": "request_route_optimization",
                "target_efficiency": 0.9,
                "current_efficiency": analysis["delivery_efficiency"]
            })
        
        # Decision based on resource utilization
        if analysis["resource_utilization"] < 0.6:  # Less than 60% utilization
            decisions.append({
                "type": "resource_optimization",
                "action": "consolidate_routes",
                "current_utilization": analysis["resource_utilization"]
            })
        elif analysis["resource_utilization"] > 0.95:  # Over 95% utilization
            decisions.append({
                "type": "capacity_expansion",
                "action": "request_additional_vehicles",
                "current_utilization": analysis["resource_utilization"]
            })
        
        # Decisions based on conflicts
        if len(conflicts) > 0:
            critical_conflicts = [c for c in conflicts if c.get("severity") == "critical"]
            if critical_conflicts:
                decisions.append({
                    "type": "emergency_response",
                    "action": "activate_emergency_protocols",
                    "critical_conflicts": len(critical_conflicts)
                })
        
        return decisions
    
    def _execute_decisions(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute strategic decisions"""
        execution_results = {
            "executed": 0,
            "failed": 0,
            "details": []
        }
        
        for decision in decisions:
            try:
                result = self._execute_single_decision(decision)
                execution_results["executed"] += 1
                execution_results["details"].append(result)
            except Exception as e:
                execution_results["failed"] += 1
                execution_results["details"].append({
                    "decision": decision,
                    "error": str(e)
                })
                logger.error(f"Failed to execute decision {decision['type']}: {e}")
        
        return execution_results
    
    def _execute_single_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single strategic decision"""
        if decision["type"] == "efficiency_improvement":
            # Request system-wide route optimization
            self.send_message(
                "route_planning_agent",
                "global_optimization",
                {
                    "target_efficiency": decision["target_efficiency"],
                    "priority": "high"
                }
            )
            
            return {
                "decision": decision["type"],
                "action": "optimization_requested",
                "status": "success"
            }
        
        elif decision["type"] == "emergency_response":
            # Activate emergency protocols
            self.send_message(
                "exception_handling_agent",
                "emergency_activation",
                {
                    "critical_conflicts": decision["critical_conflicts"],
                    "priority": "critical"
                }
            )
            
            return {
                "decision": decision["type"],
                "action": "emergency_activated",
                "status": "success"
            }
        
        return {
            "decision": decision["type"],
            "action": "no_action_defined",
            "status": "skipped"
        }