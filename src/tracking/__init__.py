"""
Real-time vehicle tracking and diagnostics module.
Provides GPS tracking, telematics integration, IoT sensors, and live monitoring capabilities.
"""

from .gps_tracker import GPSTracker, GPSLocation
from .telematics import TelematicsUnit, VehicleDiagnostics, MaintenanceAlert
from .vehicle_monitor import VehicleMonitor
from .iot_sensors import (
    IoTSensorSystem, 
    TemperatureReading, 
    CargoSensorReading, 
    EnvironmentalReading,
    SensorAlert
)
from .setup import setup_gps_tracking

__all__ = [
    'GPSTracker',
    'GPSLocation',
    'TelematicsUnit',
    'VehicleDiagnostics', 
    'MaintenanceAlert',
    'VehicleMonitor',
    'IoTSensorSystem',
    'TemperatureReading',
    'CargoSensorReading',
    'EnvironmentalReading',
    'SensorAlert',
    'setup_gps_tracking'
]