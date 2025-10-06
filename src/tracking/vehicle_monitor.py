"""
Vehicle monitoring and coordination system.
Integrates GPS tracking and telematics for comprehensive fleet management.
"""

import redis
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from .gps_tracker import GPSTracker, GPSLocation
from .telematics import TelematicsUnit, VehicleDiagnostics, MaintenanceAlert
from loguru import logger

import redis
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from .gps_tracker import GPSTracker, GPSLocation
from .telematics import TelematicsUnit, VehicleDiagnostics
from loguru import logger

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import threading
import time
from loguru import logger

from .gps_tracker import GPSTracker, GPSLocation
from .telematics import TelematicsUnit, VehicleDiagnostics, MaintenanceAlert


class VehicleMonitor:
    """Comprehensive vehicle monitoring system combining GPS and telematics"""
    
    def __init__(self, gps_tracker: GPSTracker, telematics: TelematicsUnit, iot_sensors=None):
        """Initialize vehicle monitor"""
        self.gps_tracker = gps_tracker
        self.telematics = telematics
        self.iot_sensors = iot_sensors  # Optional IoT sensor system
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Initialize tracking sets and callbacks
        self.monitored_vehicles: Set[str] = set()
        self.alert_callbacks: List[Callable] = []
        self.is_running = False
        
        logger.info("Vehicle Monitor initialized")
    
    def add_vehicle(self, vehicle_id: str, initial_location: Optional[tuple] = None) -> bool:
        """Add vehicle to comprehensive monitoring"""
        try:
            # Add to both GPS and telematics
            gps_success = self.gps_tracker.add_vehicle(vehicle_id, initial_location)
            telematics_success = self.telematics.add_vehicle(vehicle_id)
            
            if gps_success and telematics_success:
                self.monitored_vehicles.add(vehicle_id)
                logger.info(f"Added vehicle {vehicle_id} to comprehensive monitoring")
                return True
            else:
                logger.warning(f"Partial success adding vehicle {vehicle_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add vehicle {vehicle_id}: {str(e)}")
            return False
    
    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Remove vehicle from monitoring"""
        try:
            gps_removed = self.gps_tracker.remove_vehicle(vehicle_id)
            telematics_removed = self.telematics.remove_vehicle(vehicle_id)
            
            if vehicle_id in self.monitored_vehicles:
                self.monitored_vehicles.remove(vehicle_id)
            
            logger.info(f"Removed vehicle {vehicle_id} from monitoring")
            return gps_removed or telematics_removed
            
        except Exception as e:
            logger.error(f"Failed to remove vehicle {vehicle_id}: {str(e)}")
            return False
    
    def start_monitoring(self) -> bool:
        """Start comprehensive vehicle monitoring"""
        try:
            if self.is_running:
                return True
            
            # Start both subsystems
            gps_started = self.gps_tracker.start_tracking()
            telematics_started = self.telematics.start_monitoring()
            
            if gps_started and telematics_started:
                self.is_running = True
                logger.info("Vehicle monitoring started")
                return True
            else:
                logger.error("Failed to start one or more monitoring subsystems")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start monitoring: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop vehicle monitoring"""
        try:
            gps_stopped = self.gps_tracker.stop_tracking()
            telematics_stopped = self.telematics.stop_monitoring()
            
            self.is_running = False
            logger.info("Vehicle monitoring stopped")
            return gps_stopped and telematics_stopped
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
            return False
    
    def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """Get comprehensive vehicle status"""
        try:
            location = self.gps_tracker.get_current_location(vehicle_id)
            diagnostics = self.telematics.get_diagnostics(vehicle_id)
            engine_health = self.telematics.get_engine_health(vehicle_id)
            alerts = self.telematics.get_maintenance_alerts(vehicle_id)
            
            status = {
                'vehicle_id': vehicle_id,
                'timestamp': datetime.now().isoformat(),
                'location': location.to_dict() if location else None,
                'diagnostics': diagnostics.to_dict() if diagnostics else None,
                'engine_health': engine_health,
                'maintenance_alerts': [alert.to_dict() for alert in alerts],
                'alert_count': len(alerts),
                'critical_alert_count': sum(1 for alert in alerts if alert.priority >= 4),
                'is_moving': location.speed > 5 if location else False,
                'health_score': engine_health.get('health_score', 0) if engine_health else 0
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get vehicle status for {vehicle_id}: {str(e)}")
            return {'vehicle_id': vehicle_id, 'error': str(e)}
    
    def get_fleet_overview(self) -> Dict[str, Any]:
        """Get comprehensive fleet overview"""
        try:
            overview = {
                'timestamp': datetime.now(),
                'total_vehicles': len(self.monitored_vehicles),
                'active_vehicles': 0,
                'vehicles': {},
                'alerts': []
            }
            
            for vehicle_id in self.monitored_vehicles:
                vehicle_status = self.get_vehicle_status(vehicle_id)
                overview['vehicles'][vehicle_id] = vehicle_status
                
                # Count active vehicles (vehicles with recent GPS data)
                location_data = vehicle_status.get('location')
                if location_data and location_data.get('timestamp'):
                    try:
                        # Handle both string timestamp and datetime object
                        timestamp_value = location_data['timestamp']
                        if isinstance(timestamp_value, str):
                            # Clean up timezone info and parse
                            clean_timestamp = timestamp_value.replace('Z', '').replace('+00:00', '')
                            if '.' in clean_timestamp:
                                # Handle microseconds
                                last_update = datetime.fromisoformat(clean_timestamp)
                            else:
                                last_update = datetime.fromisoformat(clean_timestamp)
                        elif isinstance(timestamp_value, datetime):
                            last_update = timestamp_value
                        else:
                            logger.warning(f"Unexpected timestamp type for vehicle {vehicle_id}: {type(timestamp_value)}")
                            continue
                        
                        # Check if vehicle was active in last 5 minutes
                        time_diff = (datetime.now() - last_update).total_seconds()
                        if time_diff < 300:  # 5 minutes
                            overview['active_vehicles'] += 1
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"Invalid timestamp format for vehicle {vehicle_id}: {e}")
                        continue
                
                # Collect alerts
                diagnostics = vehicle_status.get('diagnostics', {})
                alerts = diagnostics.get('maintenance_alerts', [])
                if alerts:
                    for alert in alerts:
                        alert['vehicle_id'] = vehicle_id
                        overview['alerts'].append(alert)
            
            return overview
            
        except Exception as e:
            logger.error(f"Failed to get fleet overview: {str(e)}")
            return {'error': str(e)}
    
    def get_fleet_status(self) -> Dict[str, Any]:
        """Alias for get_fleet_overview for dashboard compatibility"""
        return self.get_fleet_overview()
    
    def get_vehicle_history(self, vehicle_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get vehicle history including location and diagnostics"""
        try:
            location_history = self.gps_tracker.get_location_history(vehicle_id, hours)
            
            history = {
                'vehicle_id': vehicle_id,
                'period_hours': hours,
                'locations': [loc.to_dict() for loc in location_history],
                'location_count': len(location_history),
                'distance_traveled': self._calculate_distance_traveled(location_history),
                'avg_speed': self._calculate_average_speed(location_history),
                'route_points': [(loc.latitude, loc.longitude) for loc in location_history]
            }
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get vehicle history for {vehicle_id}: {str(e)}")
            return {'vehicle_id': vehicle_id, 'error': str(e)}
    
    def check_geofence_violations(self, geofences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check all vehicles for geofence violations"""
        violations = []
        
        try:
            for vehicle_id in self.monitored_vehicles:
                location = self.gps_tracker.get_current_location(vehicle_id)
                if not location:
                    continue
                
                for geofence in geofences:
                    if geofence.get('type') == 'restricted':
                        # Check if vehicle is in restricted area
                        in_fence = self.gps_tracker.is_vehicle_in_geofence(
                            vehicle_id,
                            geofence['center_lat'],
                            geofence['center_lng'],
                            geofence['radius_meters']
                        )
                        
                        if in_fence:
                            violations.append({
                                'vehicle_id': vehicle_id,
                                'geofence_name': geofence.get('name', 'Unknown'),
                                'violation_type': 'unauthorized_entry',
                                'location': location.to_dict(),
                                'timestamp': datetime.now().isoformat()
                            })
                    
                    elif geofence.get('type') == 'required':
                        # Check if vehicle should be in area but isn't
                        scheduled_time = geofence.get('scheduled_time')
                        if scheduled_time and self._is_scheduled_now(scheduled_time):
                            in_fence = self.gps_tracker.is_vehicle_in_geofence(
                                vehicle_id,
                                geofence['center_lat'],
                                geofence['center_lng'],
                                geofence['radius_meters']
                            )
                            
                            if not in_fence:
                                violations.append({
                                    'vehicle_id': vehicle_id,
                                    'geofence_name': geofence.get('name', 'Unknown'),
                                    'violation_type': 'missed_checkpoint',
                                    'location': location.to_dict(),
                                    'timestamp': datetime.now().isoformat()
                                })
            
            return violations
            
        except Exception as e:
            logger.error(f"Failed to check geofence violations: {str(e)}")
            return []
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback for vehicle alerts"""
        self.alert_callbacks.append(callback)
    
    def _on_location_update(self, location: GPSLocation):
        """Handle GPS location updates"""
        try:
            # Could trigger location-based alerts here
            pass
        except Exception as e:
            logger.error(f"Error handling location update: {str(e)}")
    
    def _on_diagnostic_update(self, diagnostics: VehicleDiagnostics):
        """Handle telematics diagnostic updates"""
        try:
            # Could trigger diagnostic-based alerts here
            pass
        except Exception as e:
            logger.error(f"Error handling diagnostic update: {str(e)}")
    
    def _calculate_distance_traveled(self, locations: List[GPSLocation]) -> float:
        """Calculate total distance traveled from location history"""
        try:
            if len(locations) < 2:
                return 0.0
            
            total_distance = 0.0
            for i in range(1, len(locations)):
                prev_loc = locations[i-1]
                curr_loc = locations[i]
                
                # Simple distance calculation (Haversine)
                import math
                
                lat1, lon1 = math.radians(prev_loc.latitude), math.radians(prev_loc.longitude)
                lat2, lon2 = math.radians(curr_loc.latitude), math.radians(curr_loc.longitude)
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                
                # Distance in kilometers
                distance_km = 6371 * c
                total_distance += distance_km
            
            return round(total_distance, 2)
            
        except Exception as e:
            logger.error(f"Failed to calculate distance: {str(e)}")
            return 0.0
    
    def _calculate_average_speed(self, locations: List[GPSLocation]) -> float:
        """Calculate average speed from location history"""
        try:
            if not locations:
                return 0.0
            
            speeds = [loc.speed for loc in locations if loc.speed > 0]
            return round(sum(speeds) / len(speeds), 2) if speeds else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate average speed: {str(e)}")
            return 0.0
    
    def _is_scheduled_now(self, schedule_time: str) -> bool:
        """Check if current time matches schedule"""
        try:
            # Simple time check - could be more sophisticated
            now = datetime.now()
            # For demo, just check if within an hour of schedule
            return True  # Simplified for demo
        except Exception as e:
            logger.error(f"Failed to check schedule: {str(e)}")
            return False