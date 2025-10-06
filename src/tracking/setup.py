"""
Setup utilities for GPS tracking and telematics systems
"""

from typing import Optional, Dict, Any
from loguru import logger

from .gps_tracker import GPSTracker
from .telematics import TelematicsUnit
from .vehicle_monitor import VehicleMonitor


def setup_gps_tracking(
    api_key: Optional[str] = None,
    update_interval: int = 30,
    enable_geofencing: bool = True,
    redis_host: str = 'localhost',
    redis_port: int = 6379
) -> Dict[str, Any]:
    """
    Setup GPS tracking system with configuration
    
    Args:
        api_key: GPS service API key
        update_interval: Update interval in seconds
        enable_geofencing: Enable geofencing features
        redis_host: Redis host for data storage
        redis_port: Redis port
    
    Returns:
        Setup status and configuration
    """
    try:
        import redis
        
        # Initialize Redis connection
        redis_client = redis.Redis(host=redis_host, port=redis_port, db=0)
        
        # Test Redis connection
        redis_client.ping()
        
        # Initialize GPS tracker
        gps_tracker = GPSTracker(api_key=api_key, redis_client=redis_client)
        gps_tracker.tracking_interval = update_interval
        
        # Initialize telematics
        telematics = TelematicsUnit(redis_client=redis_client)
        
        # Initialize vehicle monitor
        vehicle_monitor = VehicleMonitor(gps_tracker=gps_tracker, telematics=telematics)
        
        # Add demo vehicles for testing
        demo_vehicles = [
            ("VEH_001", (40.7128, -74.0060)),  # NYC
            ("VEH_002", (40.6892, -74.0445)),  # Near Statue of Liberty
            ("VEH_003", (40.8176, -73.9482)),  # Bronx
        ]
        
        for vehicle_id, location in demo_vehicles:
            vehicle_monitor.add_vehicle(vehicle_id, location)
        
        # Start monitoring
        monitoring_started = vehicle_monitor.start_monitoring()
        
        setup_result = {
            'success': True,
            'gps_tracker': True,
            'telematics': True,
            'vehicle_monitor': True,
            'monitoring_started': monitoring_started,
            'demo_vehicles_added': len(demo_vehicles),
            'redis_connection': True,
            'configuration': {
                'api_key_configured': bool(api_key),
                'update_interval': update_interval,
                'geofencing_enabled': enable_geofencing,
                'redis_host': redis_host,
                'redis_port': redis_port
            }
        }
        
        logger.info("GPS tracking setup completed successfully")
        return setup_result
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'gps_tracker': False,
            'telematics': False,
            'vehicle_monitor': False,
            'monitoring_started': False,
            'redis_connection': False
        }
        
        logger.error(f"GPS tracking setup failed: {str(e)}")
        return error_result


def create_vehicle_monitor() -> Optional[VehicleMonitor]:
    """Create a vehicle monitor instance with default configuration"""
    try:
        return VehicleMonitor()
    except Exception as e:
        logger.error(f"Failed to create vehicle monitor: {str(e)}")
        return None


def get_system_status() -> Dict[str, Any]:
    """Get current system status"""
    try:
        import redis
        
        # Test Redis connection
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            redis_client.ping()
            redis_status = True
        except Exception:
            redis_status = False
        
        # Check if tracking data exists
        tracking_data_exists = False
        if redis_status:
            try:
                keys = redis_client.keys("gps:location:*")
                tracking_data_exists = len(keys) > 0
            except Exception:
                pass
        
        status = {
            'redis_available': redis_status,
            'tracking_data_exists': tracking_data_exists,
            'system_ready': redis_status,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        return {
            'redis_available': False,
            'tracking_data_exists': False,
            'system_ready': False,
            'error': str(e)
        }