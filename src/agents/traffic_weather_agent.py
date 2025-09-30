"""
Traffic & Weather Agent - Monitors real-time traffic and weather conditions.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from base_agent import BaseAgent
from models import TrafficData, WeatherData, Location, AgentState


class TrafficWeatherAgent(BaseAgent):
    """
    Monitors real-time traffic conditions and weather data
    to provide updates for route optimization.
    """
    
    def __init__(self, state_manager, llm=None):
        super().__init__("traffic_weather_agent", state_manager, llm)
        self.monitored_routes = {}
        self.traffic_data_cache = {}
        self.weather_data_cache = {}
        self.update_interval_minutes = 15
        self.last_update = None
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process traffic and weather monitoring requests"""
        self.update_state(AgentState.EXECUTING)
        
        try:
            # Check if periodic update is needed
            if self._needs_periodic_update():
                self._perform_periodic_update()
            
            # Handle specific requests
            action = input_data.get("action", "monitor")
            
            if action == "monitor_route":
                result = self._monitor_specific_route(input_data)
            elif action == "get_traffic_data":
                result = self._get_traffic_for_location(input_data)
            elif action == "get_weather_data":
                result = self._get_weather_for_location(input_data)
            elif action == "update_all":
                result = self._update_all_data()
            else:
                result = self._general_monitoring()
            
            return result
            
        except Exception as e:
            logger.error(f"Traffic & weather agent error: {e}")
            return {"error": str(e), "agent": self.name}
        
        finally:
            self.update_state(AgentState.MONITORING)
    
    def _needs_periodic_update(self) -> bool:
        """Check if periodic update is needed"""
        if not self.last_update:
            return True
        
        time_since_update = datetime.now() - self.last_update
        return time_since_update.total_seconds() > (self.update_interval_minutes * 60)
    
    def _perform_periodic_update(self):
        """Perform periodic update of traffic and weather data"""
        logger.info("Performing periodic traffic and weather update")
        
        # Update traffic data for monitored routes
        for route_id, route_info in self.monitored_routes.items():
            self._update_route_conditions(route_id, route_info)
        
        # Update general traffic conditions for major areas
        self._update_general_traffic_conditions()
        
        # Update weather conditions
        self._update_weather_conditions()
        
        self.last_update = datetime.now()
    
    def _monitor_specific_route(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor traffic and weather for a specific route"""
        vehicle_id = input_data.get("vehicle_id")
        route_stops = input_data.get("route_stops", [])
        
        if not vehicle_id or not route_stops:
            return {"error": "Missing vehicle_id or route_stops"}
        
        # Store route for monitoring
        route_id = f"route_{vehicle_id}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.monitored_routes[route_id] = {
            "vehicle_id": vehicle_id,
            "route_stops": route_stops,
            "monitoring_started": datetime.now(),
            "last_checked": None
        }
        
        # Get current conditions for the route
        route_conditions = self._analyze_route_conditions(route_stops)
        
        # Check for alerts
        alerts = self._check_for_alerts(route_conditions)
        
        # Notify relevant agents if issues found
        if alerts:
            self._send_traffic_alerts(vehicle_id, alerts)
        
        result = {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "route_id": route_id,
            "vehicle_id": vehicle_id,
            "monitoring_started": True,
            "current_conditions": route_conditions,
            "alerts": alerts
        }
        
        logger.info(f"Started monitoring route for vehicle {vehicle_id}")
        return result
    
    def _analyze_route_conditions(self, route_stops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze traffic and weather conditions for route stops"""
        conditions = {
            "traffic_analysis": [],
            "weather_analysis": [],
            "overall_impact": "low",
            "estimated_delay_minutes": 0
        }
        
        total_delay = 0
        max_impact = 0
        
        for stop in route_stops:
            location = stop.get("location")
            if location:
                # Get traffic data
                traffic_data = self._get_traffic_data(location)
                conditions["traffic_analysis"].append({
                    "stop_type": stop.get("type"),
                    "order_id": stop.get("order_id"),
                    "congestion_level": traffic_data.congestion_level,
                    "estimated_delay": traffic_data.congestion_level * 10  # Simple delay estimate
                })
                
                # Get weather data
                weather_data = self._get_weather_data(location)
                conditions["weather_analysis"].append({
                    "stop_type": stop.get("type"),
                    "order_id": stop.get("order_id"),
                    "weather_condition": weather_data.condition,
                    "impact_factor": weather_data.impact_factor,
                    "visibility_km": weather_data.visibility_km
                })
                
                # Calculate impacts
                delay = traffic_data.congestion_level * 10 + weather_data.impact_factor * 5
                total_delay += delay
                max_impact = max(max_impact, traffic_data.congestion_level, weather_data.impact_factor)
        
        conditions["estimated_delay_minutes"] = total_delay
        
        if max_impact < 0.3:
            conditions["overall_impact"] = "low"
        elif max_impact < 0.7:
            conditions["overall_impact"] = "medium"
        else:
            conditions["overall_impact"] = "high"
        
        return conditions
    
    def _get_traffic_data(self, location: Location) -> TrafficData:
        """Get traffic data for a location (simulated)"""
        # In a real implementation, this would call traffic APIs like Google Maps, HERE, etc.
        
        cache_key = f"{location.latitude:.3f},{location.longitude:.3f}"
        
        # Check cache first
        if cache_key in self.traffic_data_cache:
            cached_data = self.traffic_data_cache[cache_key]
            if (datetime.now() - cached_data.last_updated).total_seconds() < 600:  # 10 min cache
                return cached_data
        
        # Simulate traffic data based on time and location
        current_hour = datetime.now().hour
        
        # Rush hour simulation
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            congestion_level = 0.8 + (hash(cache_key) % 20) / 100  # 0.8-1.0
            average_speed = 25 + (hash(cache_key) % 15)  # 25-40 km/h
        elif 10 <= current_hour <= 16:
            congestion_level = 0.4 + (hash(cache_key) % 30) / 100  # 0.4-0.7
            average_speed = 40 + (hash(cache_key) % 20)  # 40-60 km/h
        else:
            congestion_level = 0.1 + (hash(cache_key) % 20) / 100  # 0.1-0.3
            average_speed = 50 + (hash(cache_key) % 30)  # 50-80 km/h
        
        traffic_data = TrafficData(
            location=location,
            congestion_level=min(congestion_level, 1.0),
            average_speed_kmh=average_speed
        )
        
        # Cache the data
        self.traffic_data_cache[cache_key] = traffic_data
        
        return traffic_data
    
    def _get_weather_data(self, location: Location) -> WeatherData:
        """Get weather data for a location (simulated)"""
        # In a real implementation, this would call weather APIs
        
        cache_key = f"{location.latitude:.3f},{location.longitude:.3f}"
        
        # Check cache
        if cache_key in self.weather_data_cache:
            cached_data = self.weather_data_cache[cache_key]
            if (datetime.now() - cached_data.last_updated).total_seconds() < 1800:  # 30 min cache
                return cached_data
        
        # Simulate weather data
        conditions = ["clear", "cloudy", "light_rain", "rain", "heavy_rain", "snow", "storm"]
        condition_weights = [0.4, 0.3, 0.15, 0.08, 0.04, 0.02, 0.01]  # Clear weather most common
        
        # Simple weather simulation
        hash_val = hash(cache_key + str(datetime.now().date()))
        condition_index = hash_val % len(conditions)
        condition = conditions[condition_index]
        
        # Impact factors based on condition
        impact_factors = {
            "clear": 0.0,
            "cloudy": 0.1,
            "light_rain": 0.3,
            "rain": 0.6,
            "heavy_rain": 1.0,
            "snow": 1.2,
            "storm": 1.8
        }
        
        weather_data = WeatherData(
            location=location,
            condition=condition,
            temperature_celsius=15 + (hash_val % 30),  # 15-45°C
            wind_speed_kmh=5 + (hash_val % 25),  # 5-30 km/h
            visibility_km=max(1, 20 - impact_factors[condition] * 10),
            impact_factor=impact_factors[condition]
        )
        
        # Cache the data
        self.weather_data_cache[cache_key] = weather_data
        
        return weather_data
    
    def _check_for_alerts(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for traffic and weather alerts"""
        alerts = []
        
        # Traffic alerts
        for traffic_info in conditions["traffic_analysis"]:
            if traffic_info["congestion_level"] > 0.8:
                alerts.append({
                    "type": "traffic_alert",
                    "severity": "high" if traffic_info["congestion_level"] > 0.9 else "medium",
                    "message": f"Heavy traffic congestion at {traffic_info['stop_type']} for order {traffic_info['order_id']}",
                    "estimated_delay": traffic_info["estimated_delay"],
                    "order_id": traffic_info["order_id"]
                })
        
        # Weather alerts
        for weather_info in conditions["weather_analysis"]:
            if weather_info["impact_factor"] > 1.0:
                alerts.append({
                    "type": "weather_alert",
                    "severity": "high" if weather_info["impact_factor"] > 1.5 else "medium",
                    "message": f"Severe weather ({weather_info['weather_condition']}) affecting delivery for order {weather_info['order_id']}",
                    "weather_condition": weather_info["weather_condition"],
                    "visibility_km": weather_info["visibility_km"],
                    "order_id": weather_info["order_id"]
                })
        
        # Overall delay alert
        if conditions["estimated_delay_minutes"] > 30:
            alerts.append({
                "type": "delay_alert",
                "severity": "high" if conditions["estimated_delay_minutes"] > 60 else "medium",
                "message": f"Route expected to have {conditions['estimated_delay_minutes']:.0f} minutes of delays",
                "estimated_delay": conditions["estimated_delay_minutes"]
            })
        
        return alerts
    
    def _send_traffic_alerts(self, vehicle_id: str, alerts: List[Dict[str, Any]]):
        """Send traffic alerts to relevant agents"""
        # Notify supervisor
        self.send_message(
            "supervisor_agent",
            "traffic_weather_alert",
            {
                "vehicle_id": vehicle_id,
                "alerts": alerts,
                "alert_count": len(alerts),
                "max_severity": max([a.get("severity", "low") for a in alerts], default="low")
            }
        )
        
        # Notify route planning agent for potential re-routing
        high_severity_alerts = [a for a in alerts if a.get("severity") == "high"]
        if high_severity_alerts:
            self.send_message(
                "route_planning_agent",
                "reroute_request",
                {
                    "vehicle_id": vehicle_id,
                    "reason": "traffic_weather_conditions",
                    "alerts": high_severity_alerts,
                    "priority": "high"
                }
            )
    
    def _update_route_conditions(self, route_id: str, route_info: Dict[str, Any]):
        """Update conditions for a monitored route"""
        try:
            route_stops = route_info["route_stops"]
            conditions = self._analyze_route_conditions(route_stops)
            alerts = self._check_for_alerts(conditions)
            
            # Update monitoring info
            route_info["last_checked"] = datetime.now()
            route_info["latest_conditions"] = conditions
            route_info["latest_alerts"] = alerts
            
            # Send alerts if any
            if alerts:
                self._send_traffic_alerts(route_info["vehicle_id"], alerts)
            
            logger.debug(f"Updated conditions for route {route_id}")
            
        except Exception as e:
            logger.error(f"Error updating route conditions for {route_id}: {e}")
    
    def _update_general_traffic_conditions(self):
        """Update general traffic conditions for major areas"""
        # Define major metropolitan areas (simplified)
        major_areas = [
            {"lat": 40.7128, "lng": -74.0060, "name": "NYC"},
            {"lat": 34.0522, "lng": -118.2437, "name": "LA"},
            {"lat": 41.8781, "lng": -87.6298, "name": "Chicago"},
            {"lat": 29.7604, "lng": -95.3698, "name": "Houston"}
        ]
        
        for area in major_areas:
            location = Location(latitude=area["lat"], longitude=area["lng"])
            traffic_data = self._get_traffic_data(location)
            
            # Store in cache for general access
            cache_key = f"general_{area['name']}"
            self.traffic_data_cache[cache_key] = traffic_data
    
    def _update_weather_conditions(self):
        """Update weather conditions for major areas"""
        # Similar to traffic, update weather for major areas
        major_areas = [
            {"lat": 40.7128, "lng": -74.0060, "name": "NYC"},
            {"lat": 34.0522, "lng": -118.2437, "name": "LA"},
            {"lat": 41.8781, "lng": -87.6298, "name": "Chicago"},
            {"lat": 29.7604, "lng": -95.3698, "name": "Houston"}
        ]
        
        for area in major_areas:
            location = Location(latitude=area["lat"], longitude=area["lng"])
            weather_data = self._get_weather_data(location)
            
            # Store in cache
            cache_key = f"general_{area['name']}"
            self.weather_data_cache[cache_key] = weather_data
    
    def _general_monitoring(self) -> Dict[str, Any]:
        """Perform general monitoring tasks"""
        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "monitored_routes": len(self.monitored_routes),
            "cached_traffic_data": len(self.traffic_data_cache),
            "cached_weather_data": len(self.weather_data_cache),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
    
    def _get_traffic_for_location(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get traffic data for a specific location"""
        location_data = input_data.get("location")
        if not location_data:
            return {"error": "Location data required"}
        
        location = Location(**location_data)
        traffic_data = self._get_traffic_data(location)
        
        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "location": location_data,
            "traffic_data": {
                "congestion_level": traffic_data.congestion_level,
                "average_speed_kmh": traffic_data.average_speed_kmh,
                "last_updated": traffic_data.last_updated.isoformat()
            }
        }
    
    def _get_weather_for_location(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather data for a specific location"""
        location_data = input_data.get("location")
        if not location_data:
            return {"error": "Location data required"}
        
        location = Location(**location_data)
        weather_data = self._get_weather_data(location)
        
        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "location": location_data,
            "weather_data": {
                "condition": weather_data.condition,
                "temperature_celsius": weather_data.temperature_celsius,
                "wind_speed_kmh": weather_data.wind_speed_kmh,
                "visibility_km": weather_data.visibility_km,
                "impact_factor": weather_data.impact_factor,
                "last_updated": weather_data.last_updated.isoformat()
            }
        }
    
    def _update_all_data(self) -> Dict[str, Any]:
        """Force update of all traffic and weather data"""
        # Clear caches to force refresh
        self.traffic_data_cache.clear()
        self.weather_data_cache.clear()
        
        # Perform updates
        self._update_general_traffic_conditions()
        self._update_weather_conditions()
        
        # Update monitored routes
        for route_id, route_info in self.monitored_routes.items():
            self._update_route_conditions(route_id, route_info)
        
        self.last_update = datetime.now()
        
        return {
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "action": "force_update_completed",
            "updated_routes": len(self.monitored_routes),
            "traffic_cache_entries": len(self.traffic_data_cache),
            "weather_cache_entries": len(self.weather_data_cache)
        }
    
    def _handle_message(self, message) -> Dict[str, Any]:
        """Handle messages from other agents"""
        if message.message_type == "monitor_route":
            return self.process({
                "action": "monitor_route",
                "vehicle_id": message.payload.get("vehicle_id"),
                "route_stops": message.payload.get("route_stops")
            })
        
        elif message.message_type == "get_conditions":
            location = message.payload.get("location")
            if location:
                traffic_result = self._get_traffic_for_location({"location": location})
                weather_result = self._get_weather_for_location({"location": location})
                
                return {
                    "traffic": traffic_result["traffic_data"],
                    "weather": weather_result["weather_data"]
                }
        
        elif message.message_type == "stop_monitoring":
            route_id = message.payload.get("route_id")
            if route_id in self.monitored_routes:
                del self.monitored_routes[route_id]
                return {"route_monitoring_stopped": route_id}
        
        return super()._handle_message(message)