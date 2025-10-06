"""
IoT Sensor System for Temperature, Cargo, and Environmental Monitoring

This module provides comprehensive IoT sensor integration for:
- Temperature monitoring (cold chain compliance)
- Cargo status monitoring (weight, door sensors, security)
- Environmental monitoring (humidity, shock detection, air quality)
"""

import json
import time
import random
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import redis
from loguru import logger


@dataclass
class TemperatureReading:
    """Temperature sensor reading"""
    sensor_id: str
    vehicle_id: str
    temperature_celsius: float
    humidity_percent: float
    timestamp: datetime
    location: str = "cargo_bay"
    alert_threshold_min: float = -18.0  # For frozen goods
    alert_threshold_max: float = 4.0    # For refrigerated goods
    
    def is_within_range(self) -> bool:
        """Check if temperature is within acceptable range"""
        return self.alert_threshold_min <= self.temperature_celsius <= self.alert_threshold_max
    
    def get_alert_level(self) -> str:
        """Get alert level based on temperature deviation"""
        if self.is_within_range():
            return "normal"
        
        deviation = min(
            abs(self.temperature_celsius - self.alert_threshold_min),
            abs(self.temperature_celsius - self.alert_threshold_max)
        )
        
        if deviation > 10:
            return "critical"
        elif deviation > 5:
            return "high"
        else:
            return "medium"


@dataclass
class CargoSensorReading:
    """Cargo monitoring sensor reading"""
    sensor_id: str
    vehicle_id: str
    weight_kg: float
    door_status: str  # "closed", "open", "breach"
    security_seal_intact: bool
    vibration_level: float
    timestamp: datetime
    location: str = "cargo_bay"
    expected_weight_kg: Optional[float] = None
    
    def get_weight_variance(self) -> Optional[float]:
        """Calculate weight variance from expected"""
        if self.expected_weight_kg:
            return abs(self.weight_kg - self.expected_weight_kg)
        return None
    
    def has_security_alert(self) -> bool:
        """Check for security-related alerts"""
        return (
            self.door_status == "breach" or 
            not self.security_seal_intact or
            self.vibration_level > 8.0
        )


@dataclass
class EnvironmentalReading:
    """Environmental sensor reading"""
    sensor_id: str
    vehicle_id: str
    air_quality_index: int
    noise_level_db: float
    light_level_lux: float
    pressure_hpa: float
    co2_ppm: int
    timestamp: datetime
    location: str = "cabin"
    
    def get_air_quality_status(self) -> str:
        """Get air quality status based on AQI"""
        if self.air_quality_index <= 50:
            return "good"
        elif self.air_quality_index <= 100:
            return "moderate"
        elif self.air_quality_index <= 150:
            return "unhealthy_sensitive"
        elif self.air_quality_index <= 200:
            return "unhealthy"
        else:
            return "hazardous"


@dataclass
class SensorAlert:
    """Sensor-based alert"""
    alert_id: str
    sensor_id: str
    vehicle_id: str
    alert_type: str  # "temperature", "cargo", "environmental"
    severity: str    # "critical", "high", "medium", "low"
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None


class IoTSensorSystem:
    """
    IoT Sensor System for comprehensive vehicle and cargo monitoring
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize IoT sensor system"""
        self.redis_client = redis_client or redis.Redis(
            host='localhost', port=6379, db=0, decode_responses=True
        )
        
        # Sensor configuration
        self.temperature_sensors: Dict[str, Dict] = {}
        self.cargo_sensors: Dict[str, Dict] = {}
        self.environmental_sensors: Dict[str, Dict] = {}
        
        # Alert management
        self.active_alerts: Dict[str, SensorAlert] = {}
        self.alert_thresholds = self._load_alert_thresholds()
        
        # Demo/simulation control
        self.simulation_running = False
        self.simulation_thread: Optional[threading.Thread] = None
        
        logger.info("IoT Sensor System initialized")
    
    def _load_alert_thresholds(self) -> Dict[str, Any]:
        """Load alert thresholds configuration"""
        return {
            "temperature": {
                "frozen_goods": {"min": -20, "max": -15},
                "refrigerated": {"min": 0, "max": 4},
                "ambient": {"min": 15, "max": 25}
            },
            "cargo": {
                "weight_variance_threshold": 50.0,  # kg
                "max_vibration": 8.0,
                "door_open_max_duration": 300  # seconds
            },
            "environmental": {
                "max_co2_ppm": 1000,
                "max_noise_db": 85,
                "min_air_quality": 100
            }
        }
    
    def register_temperature_sensor(
        self, 
        sensor_id: str, 
        vehicle_id: str, 
        location: str = "cargo_bay",
        cargo_type: str = "ambient"
    ) -> bool:
        """Register a temperature sensor"""
        try:
            thresholds = self.alert_thresholds["temperature"].get(cargo_type, {"min": 0, "max": 25})
            
            sensor_config = {
                "sensor_id": sensor_id,
                "vehicle_id": vehicle_id,
                "location": location,
                "cargo_type": cargo_type,
                "min_threshold": thresholds["min"],
                "max_threshold": thresholds["max"],
                "active": True,
                "last_reading": None
            }
            
            self.temperature_sensors[sensor_id] = sensor_config
            
            # Store in Redis
            self.redis_client.hset(
                f"sensor:temperature:{sensor_id}",
                mapping=sensor_config
            )
            
            logger.info(f"Registered temperature sensor {sensor_id} for vehicle {vehicle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register temperature sensor {sensor_id}: {str(e)}")
            return False
    
    def register_cargo_sensor(
        self, 
        sensor_id: str, 
        vehicle_id: str, 
        expected_weight: Optional[float] = None
    ) -> bool:
        """Register a cargo monitoring sensor"""
        try:
            sensor_config = {
                "sensor_id": sensor_id,
                "vehicle_id": vehicle_id,
                "expected_weight": expected_weight,
                "active": True,
                "last_reading": None
            }
            
            self.cargo_sensors[sensor_id] = sensor_config
            
            # Store in Redis
            self.redis_client.hset(
                f"sensor:cargo:{sensor_id}",
                mapping=sensor_config
            )
            
            logger.info(f"Registered cargo sensor {sensor_id} for vehicle {vehicle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register cargo sensor {sensor_id}: {str(e)}")
            return False
    
    def register_environmental_sensor(
        self, 
        sensor_id: str, 
        vehicle_id: str, 
        location: str = "cabin"
    ) -> bool:
        """Register an environmental sensor"""
        try:
            sensor_config = {
                "sensor_id": sensor_id,
                "vehicle_id": vehicle_id,
                "location": location,
                "active": True,
                "last_reading": None
            }
            
            self.environmental_sensors[sensor_id] = sensor_config
            
            # Store in Redis
            self.redis_client.hset(
                f"sensor:environmental:{sensor_id}",
                mapping=sensor_config
            )
            
            logger.info(f"Registered environmental sensor {sensor_id} for vehicle {vehicle_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register environmental sensor {sensor_id}: {str(e)}")
            return False
    
    def record_temperature_reading(self, reading: TemperatureReading) -> bool:
        """Record a temperature sensor reading"""
        try:
            # Store reading in Redis with timestamp as score
            timestamp_score = reading.timestamp.timestamp()
            
            self.redis_client.zadd(
                f"readings:temperature:{reading.sensor_id}",
                {json.dumps(asdict(reading), default=str): timestamp_score}
            )
            
            # Keep only last 1000 readings per sensor
            self.redis_client.zremrangebyrank(
                f"readings:temperature:{reading.sensor_id}", 0, -1001
            )
            
            # Update sensor status
            if reading.sensor_id in self.temperature_sensors:
                self.temperature_sensors[reading.sensor_id]["last_reading"] = reading.timestamp
            
            # Check for alerts
            self._check_temperature_alerts(reading)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record temperature reading: {str(e)}")
            return False
    
    def record_cargo_reading(self, reading: CargoSensorReading) -> bool:
        """Record a cargo sensor reading"""
        try:
            # Store reading in Redis
            timestamp_score = reading.timestamp.timestamp()
            
            self.redis_client.zadd(
                f"readings:cargo:{reading.sensor_id}",
                {json.dumps(asdict(reading), default=str): timestamp_score}
            )
            
            # Keep only last 1000 readings per sensor
            self.redis_client.zremrangebyrank(
                f"readings:cargo:{reading.sensor_id}", 0, -1001
            )
            
            # Update sensor status
            if reading.sensor_id in self.cargo_sensors:
                self.cargo_sensors[reading.sensor_id]["last_reading"] = reading.timestamp
            
            # Check for alerts
            self._check_cargo_alerts(reading)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record cargo reading: {str(e)}")
            return False
    
    def record_environmental_reading(self, reading: EnvironmentalReading) -> bool:
        """Record an environmental sensor reading"""
        try:
            # Store reading in Redis
            timestamp_score = reading.timestamp.timestamp()
            
            self.redis_client.zadd(
                f"readings:environmental:{reading.sensor_id}",
                {json.dumps(asdict(reading), default=str): timestamp_score}
            )
            
            # Keep only last 1000 readings per sensor
            self.redis_client.zremrangebyrank(
                f"readings:environmental:{reading.sensor_id}", 0, -1001
            )
            
            # Update sensor status
            if reading.sensor_id in self.environmental_sensors:
                self.environmental_sensors[reading.sensor_id]["last_reading"] = reading.timestamp
            
            # Check for alerts
            self._check_environmental_alerts(reading)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record environmental reading: {str(e)}")
            return False
    
    def _check_temperature_alerts(self, reading: TemperatureReading):
        """Check temperature reading for alert conditions"""
        if not reading.is_within_range():
            alert_id = f"temp_{reading.sensor_id}_{int(reading.timestamp.timestamp())}"
            
            alert = SensorAlert(
                alert_id=alert_id,
                sensor_id=reading.sensor_id,
                vehicle_id=reading.vehicle_id,
                alert_type="temperature",
                severity=reading.get_alert_level(),
                message=f"Temperature {reading.temperature_celsius}°C outside range "
                       f"({reading.alert_threshold_min}°C to {reading.alert_threshold_max}°C)",
                timestamp=reading.timestamp
            )
            
            self._create_alert(alert)
    
    def _check_cargo_alerts(self, reading: CargoSensorReading):
        """Check cargo reading for alert conditions"""
        alerts = []
        
        # Check security alerts
        if reading.has_security_alert():
            alert_id = f"cargo_security_{reading.sensor_id}_{int(reading.timestamp.timestamp())}"
            
            message_parts = []
            if reading.door_status == "breach":
                message_parts.append("Door breach detected")
            if not reading.security_seal_intact:
                message_parts.append("Security seal compromised")
            if reading.vibration_level > 8.0:
                message_parts.append(f"High vibration: {reading.vibration_level}")
            
            alert = SensorAlert(
                alert_id=alert_id,
                sensor_id=reading.sensor_id,
                vehicle_id=reading.vehicle_id,
                alert_type="cargo_security",
                severity="critical" if reading.door_status == "breach" else "high",
                message="; ".join(message_parts),
                timestamp=reading.timestamp
            )
            
            self._create_alert(alert)
        
        # Check weight variance
        weight_variance = reading.get_weight_variance()
        if weight_variance and weight_variance > self.alert_thresholds["cargo"]["weight_variance_threshold"]:
            alert_id = f"cargo_weight_{reading.sensor_id}_{int(reading.timestamp.timestamp())}"
            
            alert = SensorAlert(
                alert_id=alert_id,
                sensor_id=reading.sensor_id,
                vehicle_id=reading.vehicle_id,
                alert_type="cargo_weight",
                severity="medium",
                message=f"Weight variance: {weight_variance:.1f}kg from expected",
                timestamp=reading.timestamp
            )
            
            self._create_alert(alert)
    
    def _check_environmental_alerts(self, reading: EnvironmentalReading):
        """Check environmental reading for alert conditions"""
        # Check CO2 levels
        if reading.co2_ppm > self.alert_thresholds["environmental"]["max_co2_ppm"]:
            alert_id = f"env_co2_{reading.sensor_id}_{int(reading.timestamp.timestamp())}"
            
            alert = SensorAlert(
                alert_id=alert_id,
                sensor_id=reading.sensor_id,
                vehicle_id=reading.vehicle_id,
                alert_type="environmental_co2",
                severity="high" if reading.co2_ppm > 1500 else "medium",
                message=f"High CO2 level: {reading.co2_ppm}ppm",
                timestamp=reading.timestamp
            )
            
            self._create_alert(alert)
        
        # Check noise levels
        if reading.noise_level_db > self.alert_thresholds["environmental"]["max_noise_db"]:
            alert_id = f"env_noise_{reading.sensor_id}_{int(reading.timestamp.timestamp())}"
            
            alert = SensorAlert(
                alert_id=alert_id,
                sensor_id=reading.sensor_id,
                vehicle_id=reading.vehicle_id,
                alert_type="environmental_noise",
                severity="medium",
                message=f"High noise level: {reading.noise_level_db:.1f}dB",
                timestamp=reading.timestamp
            )
            
            self._create_alert(alert)
    
    def _create_alert(self, alert: SensorAlert):
        """Create and store a sensor alert"""
        try:
            self.active_alerts[alert.alert_id] = alert
            
            # Store in Redis
            self.redis_client.hset(
                f"alert:sensor:{alert.alert_id}",
                mapping=asdict(alert)
            )
            
            logger.warning(f"Sensor alert created: {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to create sensor alert: {str(e)}")
    
    def get_sensor_readings(
        self, 
        sensor_type: str, 
        sensor_id: str, 
        limit: int = 100
    ) -> List[Dict]:
        """Get recent sensor readings"""
        try:
            readings = self.redis_client.zrevrange(
                f"readings:{sensor_type}:{sensor_id}",
                0, limit - 1,
                withscores=False
            )
            
            return [json.loads(reading) for reading in readings] if readings else []
            
        except Exception as e:
            logger.error(f"Failed to get sensor readings: {str(e)}")
            return []
    
    def get_vehicle_sensor_status(self, vehicle_id: str) -> Dict[str, Any]:
        """Get comprehensive sensor status for a vehicle"""
        try:
            status = {
                "vehicle_id": vehicle_id,
                "temperature_sensors": {},
                "cargo_sensors": {},
                "environmental_sensors": {},
                "active_alerts": [],
                "last_updated": datetime.now()
            }
            
            # Get temperature sensors for vehicle
            for sensor_id, config in self.temperature_sensors.items():
                if config["vehicle_id"] == vehicle_id:
                    latest_readings = self.get_sensor_readings("temperature", sensor_id, 1)
                    status["temperature_sensors"][sensor_id] = {
                        "config": config,
                        "latest_reading": latest_readings[0] if latest_readings else None
                    }
            
            # Get cargo sensors for vehicle
            for sensor_id, config in self.cargo_sensors.items():
                if config["vehicle_id"] == vehicle_id:
                    latest_readings = self.get_sensor_readings("cargo", sensor_id, 1)
                    status["cargo_sensors"][sensor_id] = {
                        "config": config,
                        "latest_reading": latest_readings[0] if latest_readings else None
                    }
            
            # Get environmental sensors for vehicle
            for sensor_id, config in self.environmental_sensors.items():
                if config["vehicle_id"] == vehicle_id:
                    latest_readings = self.get_sensor_readings("environmental", sensor_id, 1)
                    status["environmental_sensors"][sensor_id] = {
                        "config": config,
                        "latest_reading": latest_readings[0] if latest_readings else None
                    }
            
            # Get active alerts for vehicle
            for alert_id, alert in self.active_alerts.items():
                if alert.vehicle_id == vehicle_id and not alert.resolved:
                    status["active_alerts"].append(asdict(alert))
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get vehicle sensor status: {str(e)}")
            return {"vehicle_id": vehicle_id, "error": str(e)}
    
    def start_demo_sensors(self, vehicle_ids: Optional[List[str]] = None):
        """Start demo sensor data simulation"""
        if self.simulation_running:
            logger.warning("Demo sensor simulation already running")
            return
        
        if vehicle_ids is None:
            vehicle_ids = ["VEH_001", "VEH_002", "VEH_003"]
        
        # Register demo sensors
        for vehicle_id in vehicle_ids:
            # Temperature sensors for different cargo types
            self.register_temperature_sensor(f"TEMP_{vehicle_id}_FROZEN", vehicle_id, "cargo_bay", "frozen_goods")
            self.register_temperature_sensor(f"TEMP_{vehicle_id}_REFRIG", vehicle_id, "cargo_bay", "refrigerated")
            
            # Cargo sensors
            self.register_cargo_sensor(f"CARGO_{vehicle_id}", vehicle_id, expected_weight=1500.0)
            
            # Environmental sensors
            self.register_environmental_sensor(f"ENV_{vehicle_id}", vehicle_id, "cabin")
        
        self.simulation_running = True
        self.simulation_thread = threading.Thread(target=self._run_demo_simulation, args=(vehicle_ids,))
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        
        logger.info(f"Started demo sensor simulation for vehicles: {vehicle_ids}")
    
    def _run_demo_simulation(self, vehicle_ids: List[str]):
        """Run demo sensor data simulation"""
        while self.simulation_running:
            try:
                current_time = datetime.now()
                
                for vehicle_id in vehicle_ids:
                    # Generate temperature readings
                    temp_frozen = TemperatureReading(
                        sensor_id=f"TEMP_{vehicle_id}_FROZEN",
                        vehicle_id=vehicle_id,
                        temperature_celsius=random.uniform(-22, -15) + random.gauss(0, 2),
                        humidity_percent=random.uniform(80, 95),
                        timestamp=current_time,
                        location="cargo_bay",
                        alert_threshold_min=-20,
                        alert_threshold_max=-15
                    )
                    self.record_temperature_reading(temp_frozen)
                    
                    temp_refrig = TemperatureReading(
                        sensor_id=f"TEMP_{vehicle_id}_REFRIG",
                        vehicle_id=vehicle_id,
                        temperature_celsius=random.uniform(-2, 6) + random.gauss(0, 1),
                        humidity_percent=random.uniform(85, 95),
                        timestamp=current_time,
                        location="cargo_bay",
                        alert_threshold_min=0,
                        alert_threshold_max=4
                    )
                    self.record_temperature_reading(temp_refrig)
                    
                    # Generate cargo readings
                    cargo_reading = CargoSensorReading(
                        sensor_id=f"CARGO_{vehicle_id}",
                        vehicle_id=vehicle_id,
                        weight_kg=1500.0 + random.gauss(0, 20),
                        door_status=random.choices(
                            ["closed", "open", "breach"], 
                            weights=[85, 14, 1]
                        )[0],
                        security_seal_intact=random.random() > 0.02,
                        vibration_level=random.uniform(0, 10),
                        timestamp=current_time,
                        expected_weight_kg=1500.0
                    )
                    self.record_cargo_reading(cargo_reading)
                    
                    # Generate environmental readings
                    env_reading = EnvironmentalReading(
                        sensor_id=f"ENV_{vehicle_id}",
                        vehicle_id=vehicle_id,
                        air_quality_index=random.randint(20, 150),
                        noise_level_db=random.uniform(40, 90),
                        light_level_lux=random.uniform(50, 500),
                        pressure_hpa=random.uniform(1010, 1020),
                        co2_ppm=random.randint(400, 1200),
                        timestamp=current_time
                    )
                    self.record_environmental_reading(env_reading)
                
                time.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in demo sensor simulation: {str(e)}")
                time.sleep(5)
    
    def stop_demo_sensors(self):
        """Stop demo sensor simulation"""
        if self.simulation_running:
            self.simulation_running = False
            if self.simulation_thread:
                self.simulation_thread.join(timeout=5)
            logger.info("Demo sensor simulation stopped")
        else:
            logger.warning("Demo sensor simulation not running")
    
    def clear_sensor_data(self):
        """Clear all sensor data"""
        try:
            # Clear sensor configurations
            self.temperature_sensors.clear()
            self.cargo_sensors.clear()
            self.environmental_sensors.clear()
            self.active_alerts.clear()
            
            # Clear Redis data
            for key in self.redis_client.scan_iter(match="sensor:*"):
                self.redis_client.delete(key)
            for key in self.redis_client.scan_iter(match="readings:*"):
                self.redis_client.delete(key)
            for key in self.redis_client.scan_iter(match="alert:sensor:*"):
                self.redis_client.delete(key)
            
            logger.info("Sensor data cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear sensor data: {str(e)}")