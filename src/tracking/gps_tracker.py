"""
GPS Tracker implementation for real-time vehicle location tracking.
Provides interface for GPS hardware devices and location services.
"""

import time
import json
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
import redis
from loguru import logger

@dataclass
class GPSLocation:
    """GPS location data structure"""
    vehicle_id: str
    latitude: float
    longitude: float
    altitude: Optional[float]
    speed: float  # km/h
    heading: float  # degrees
    accuracy: float  # meters
    timestamp: datetime
    satellite_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GPSLocation':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class GPSTracker:
    """Real-time GPS tracking system for fleet vehicles"""
    
    def __init__(self, api_key: Optional[str] = None, redis_client: Optional[redis.Redis] = None):
        self.api_key = api_key or "demo_gps_tracker"
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.tracking_interval = 30  # seconds
        self.is_tracking = False
        self.tracked_vehicles = {}
        self.location_callbacks = []
        self.tracking_thread = None
        
        # Simulated GPS data for demo purposes
        self.demo_routes = {
            "VEH_001": [
                (40.7128, -74.0060),  # NYC
                (40.7589, -73.9851),  # Times Square
                (40.7614, -73.9776),  # Central Park
                (40.7505, -73.9934),  # Penn Station
            ],
            "VEH_002": [
                (40.6892, -74.0445),  # Statue of Liberty area
                (40.7282, -74.0776),  # Jersey City
                (40.7505, -73.9934),  # Penn Station
                (40.7128, -74.0060),  # Back to start
            ],
            "VEH_003": [
                (40.8176, -73.9482),  # Bronx
                (40.7829, -73.9654),  # Upper Manhattan
                (40.7589, -73.9851),  # Times Square
                (40.7128, -74.0060),  # Downtown
            ]
        }
        
        # Current position indices for demo
        self.demo_positions = {vid: 0 for vid in self.demo_routes.keys()}
        
        logger.info("GPS Tracker initialized")
    
    def add_vehicle(self, vehicle_id: str, initial_location: Optional[Tuple[float, float]] = None) -> bool:
        """Add vehicle to tracking system"""
        try:
            if initial_location:
                lat, lng = initial_location
            else:
                # Use first position from demo route or default
                if vehicle_id in self.demo_routes:
                    lat, lng = self.demo_routes[vehicle_id][0]
                else:
                    lat, lng = 40.7128, -74.0060  # Default NYC location
            
            location = GPSLocation(
                vehicle_id=vehicle_id,
                latitude=lat,
                longitude=lng,
                altitude=10.0,
                speed=0.0,
                heading=0.0,
                accuracy=5.0,
                timestamp=datetime.now(),
                satellite_count=8
            )
            
            self.tracked_vehicles[vehicle_id] = location
            self._store_location(location)
            
            logger.info(f"Added vehicle {vehicle_id} to GPS tracking")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vehicle {vehicle_id}: {str(e)}")
            return False
    
    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Remove vehicle from tracking"""
        try:
            if vehicle_id in self.tracked_vehicles:
                del self.tracked_vehicles[vehicle_id]
                self.redis_client.delete(f"gps:location:{vehicle_id}")
                logger.info(f"Removed vehicle {vehicle_id} from tracking")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove vehicle {vehicle_id}: {str(e)}")
            return False
    
    def get_current_location(self, vehicle_id: str) -> Optional[GPSLocation]:
        """Get current location of a vehicle"""
        try:
            if vehicle_id in self.tracked_vehicles:
                return self.tracked_vehicles[vehicle_id]
            
            # Try to load from Redis
            data = self.redis_client.get(f"gps:location:{vehicle_id}")
            if data:
                location_data = json.loads(data)
                return GPSLocation.from_dict(location_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get location for {vehicle_id}: {str(e)}")
            return None
    
    def get_location_history(self, vehicle_id: str, hours: int = 24) -> List[GPSLocation]:
        """Get location history for a vehicle"""
        try:
            history_key = f"gps:history:{vehicle_id}"
            history_data = self.redis_client.lrange(history_key, 0, -1)
            
            locations = []
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for data in history_data:
                location_data = json.loads(data)
                location = GPSLocation.from_dict(location_data)
                if location.timestamp >= cutoff_time:
                    locations.append(location)
            
            return sorted(locations, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to get history for {vehicle_id}: {str(e)}")
            return []
    
    def start_tracking(self) -> bool:
        """Start real-time GPS tracking"""
        try:
            if self.is_tracking:
                return True
                
            self.is_tracking = True
            self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self.tracking_thread.start()
            
            logger.info("GPS tracking started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start tracking: {str(e)}")
            return False
    
    def stop_tracking(self) -> bool:
        """Stop GPS tracking"""
        try:
            self.is_tracking = False
            if hasattr(self, 'tracking_thread'):
                self.tracking_thread.join(timeout=5)
            
            logger.info("GPS tracking stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop tracking: {str(e)}")
            return False
    
    def add_location_callback(self, callback: Callable[[GPSLocation], None]):
        """Add callback function for location updates"""
        self.location_callbacks.append(callback)
    
    def _tracking_loop(self):
        """Main tracking loop running in separate thread"""
        while self.is_tracking:
            try:
                for vehicle_id in list(self.tracked_vehicles.keys()):
                    new_location = self._simulate_gps_update(vehicle_id)
                    if new_location:
                        self.tracked_vehicles[vehicle_id] = new_location
                        self._store_location(new_location)
                        
                        # Trigger callbacks
                        for callback in self.location_callbacks:
                            try:
                                callback(new_location)
                            except Exception as e:
                                logger.warning(f"Location callback failed: {str(e)}")
                
                time.sleep(self.tracking_interval)
                
            except Exception as e:
                logger.error(f"Error in tracking loop: {str(e)}")
                time.sleep(5)
    
    def _simulate_gps_update(self, vehicle_id: str) -> Optional[GPSLocation]:
        """Simulate GPS data for demo purposes"""
        try:
            current_location = self.tracked_vehicles.get(vehicle_id)
            if not current_location:
                return None
            
            # Use demo route if available
            if vehicle_id in self.demo_routes:
                route = self.demo_routes[vehicle_id]
                current_pos = self.demo_positions[vehicle_id]
                
                # Move to next position
                next_pos = (current_pos + 1) % len(route)
                target_lat, target_lng = route[next_pos]
                
                # Simulate gradual movement
                current_lat = current_location.latitude
                current_lng = current_location.longitude
                
                # Move 10% of the way to target each update
                new_lat = current_lat + (target_lat - current_lat) * 0.1
                new_lng = current_lng + (target_lng - current_lng) * 0.1
                
                # Update position if we're close enough to target
                if abs(new_lat - target_lat) < 0.001 and abs(new_lng - target_lng) < 0.001:
                    self.demo_positions[vehicle_id] = next_pos
                    new_lat, new_lng = target_lat, target_lng
            else:
                # Random movement for vehicles without predefined routes
                import random
                new_lat = current_location.latitude + random.uniform(-0.001, 0.001)
                new_lng = current_location.longitude + random.uniform(-0.001, 0.001)
            
            # Simulate other GPS parameters
            import random
            speed = random.uniform(20, 60)  # km/h
            heading = random.uniform(0, 360)
            accuracy = random.uniform(3, 8)
            
            new_location = GPSLocation(
                vehicle_id=vehicle_id,
                latitude=new_lat,
                longitude=new_lng,
                altitude=10.0 + random.uniform(-2, 2),
                speed=speed,
                heading=heading,
                accuracy=accuracy,
                timestamp=datetime.now(),
                satellite_count=random.randint(6, 12)
            )
            
            return new_location
            
        except Exception as e:
            logger.error(f"Failed to simulate GPS update for {vehicle_id}: {str(e)}")
            return None
    
    def _store_location(self, location: GPSLocation):
        """Store location data in Redis"""
        try:
            # Store current location
            current_key = f"gps:location:{location.vehicle_id}"
            self.redis_client.setex(current_key, 3600, json.dumps(location.to_dict()))
            
            # Store in history
            history_key = f"gps:history:{location.vehicle_id}"
            self.redis_client.lpush(history_key, json.dumps(location.to_dict()))
            self.redis_client.ltrim(history_key, 0, 1000)  # Keep last 1000 entries
            self.redis_client.expire(history_key, 86400 * 7)  # 7 days
            
        except Exception as e:
            logger.error(f"Failed to store location: {str(e)}")
    
    def get_all_vehicles_locations(self) -> Dict[str, GPSLocation]:
        """Get current locations of all tracked vehicles"""
        locations = {}
        for vehicle_id in self.tracked_vehicles:
            location = self.get_current_location(vehicle_id)
            if location:
                locations[vehicle_id] = location
        return locations
    
    def is_vehicle_in_geofence(self, vehicle_id: str, center_lat: float, center_lng: float, radius_meters: float) -> bool:
        """Check if vehicle is within a geofenced area"""
        try:
            location = self.get_current_location(vehicle_id)
            if not location:
                return False
            
            # Calculate distance using Haversine formula
            import math
            
            lat1, lon1 = math.radians(location.latitude), math.radians(location.longitude)
            lat2, lon2 = math.radians(center_lat), math.radians(center_lng)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Radius of earth in meters
            distance = 6371000 * c
            
            return distance <= radius_meters
            
        except Exception as e:
            logger.error(f"Failed to check geofence for {vehicle_id}: {str(e)}")
            return False
    
    def start_demo_routes(self) -> bool:
        """Start demo vehicle routes for testing"""
        try:
            # Add demo vehicles if not already added
            demo_vehicles = ["VEH_001", "VEH_002", "VEH_003"]
            for vehicle_id in demo_vehicles:
                if vehicle_id not in self.tracked_vehicles:
                    self.add_vehicle(vehicle_id)
            
            # Start tracking if not already running
            if not self.is_tracking:
                return self.start_tracking()
            
            logger.info("Demo routes started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start demo routes: {str(e)}")
            return False
    
    def stop_demo_routes(self) -> bool:
        """Stop demo vehicle routes"""
        try:
            return self.stop_tracking()
            
        except Exception as e:
            logger.error(f"Failed to stop demo routes: {str(e)}")
            return False
    
    def clear_vehicle_data(self) -> bool:
        """Clear all vehicle tracking data"""
        try:
            # Stop tracking first
            self.stop_tracking()
            
            # Clear tracked vehicles
            self.tracked_vehicles.clear()
            
            # Clear Redis data
            for key in self.redis_client.scan_iter(match="gps:*"):
                self.redis_client.delete(key)
            
            logger.info("Vehicle tracking data cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear vehicle data: {str(e)}")
            return False