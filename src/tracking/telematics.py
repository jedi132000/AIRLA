"""
Telematics Unit implementation for vehicle diagnostics and health monitoring.
Provides interface for vehicle sensors, engine diagnostics, and performance metrics.
"""

import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import redis
from loguru import logger

@dataclass
class VehicleDiagnostics:
    """Vehicle diagnostic data structure"""
    vehicle_id: str
    engine_temp: float  # Celsius
    oil_pressure: float  # PSI
    fuel_level: float  # Percentage (0-100)
    battery_voltage: float  # Volts
    rpm: int
    speed: float  # km/h
    odometer: float  # km
    fuel_consumption: float  # L/100km
    engine_hours: float
    transmission_temp: float  # Celsius
    brake_pad_wear: float  # Percentage (0-100, 0 = new)
    tire_pressure_fl: float  # PSI (Front Left)
    tire_pressure_fr: float  # PSI (Front Right) 
    tire_pressure_rl: float  # PSI (Rear Left)
    tire_pressure_rr: float  # PSI (Rear Right)
    engine_fault_codes: List[str]
    maintenance_alerts: List[str]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VehicleDiagnostics':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class MaintenanceAlert:
    """Maintenance alert data structure"""
    vehicle_id: str
    alert_type: str  # 'warning', 'critical', 'info'
    component: str
    message: str
    priority: int  # 1-5, 5 being critical
    estimated_service_date: Optional[datetime]
    mileage_threshold: Optional[float]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.estimated_service_date:
            data['estimated_service_date'] = self.estimated_service_date.isoformat()
        return data


class TelematicsUnit:
    """Vehicle telematics system for diagnostics and health monitoring"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client or redis.Redis(host='localhost', port=6379, db=0)
        self.monitoring_interval = 60  # seconds
        self.is_monitoring = False
        self.monitored_vehicles = {}
        self.diagnostic_callbacks = []
        
        # Maintenance thresholds
        self.maintenance_thresholds = {
            'engine_temp': {'warning': 95, 'critical': 105},  # Celsius
            'oil_pressure': {'warning': 20, 'critical': 15},  # PSI
            'fuel_level': {'warning': 15, 'critical': 5},  # Percentage
            'battery_voltage': {'warning': 11.5, 'critical': 11.0},  # Volts
            'brake_pad_wear': {'warning': 80, 'critical': 90},  # Percentage
            'tire_pressure': {'warning': 28, 'critical': 25},  # PSI
        }
        
        logger.info("Telematics Unit initialized")
    
    def add_vehicle(self, vehicle_id: str) -> bool:
        """Add vehicle to telematics monitoring"""
        try:
            # Initialize with baseline diagnostics
            diagnostics = VehicleDiagnostics(
                vehicle_id=vehicle_id,
                engine_temp=85.0,
                oil_pressure=35.0,
                fuel_level=75.0,
                battery_voltage=12.4,
                rpm=0,
                speed=0.0,
                odometer=50000.0,
                fuel_consumption=8.5,
                engine_hours=2500.0,
                transmission_temp=70.0,
                brake_pad_wear=25.0,
                tire_pressure_fl=32.0,
                tire_pressure_fr=32.0,
                tire_pressure_rl=30.0,
                tire_pressure_rr=30.0,
                engine_fault_codes=[],
                maintenance_alerts=[],
                timestamp=datetime.now()
            )
            
            self.monitored_vehicles[vehicle_id] = diagnostics
            self._store_diagnostics(diagnostics)
            
            logger.info(f"Added vehicle {vehicle_id} to telematics monitoring")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vehicle {vehicle_id} to telematics: {str(e)}")
            return False
    
    def remove_vehicle(self, vehicle_id: str) -> bool:
        """Remove vehicle from telematics monitoring"""
        try:
            if vehicle_id in self.monitored_vehicles:
                del self.monitored_vehicles[vehicle_id]
                self.redis_client.delete(f"telematics:diagnostics:{vehicle_id}")
                logger.info(f"Removed vehicle {vehicle_id} from telematics")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove vehicle {vehicle_id}: {str(e)}")
            return False
    
    def get_diagnostics(self, vehicle_id: str) -> Optional[VehicleDiagnostics]:
        """Get current diagnostics for a vehicle"""
        try:
            if vehicle_id in self.monitored_vehicles:
                return self.monitored_vehicles[vehicle_id]
            
            # Try to load from Redis
            data = self.redis_client.get(f"telematics:diagnostics:{vehicle_id}")
            if data:
                diagnostic_data = json.loads(data.decode('utf-8'))
                return VehicleDiagnostics.from_dict(diagnostic_data)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get diagnostics for {vehicle_id}: {str(e)}")
            return None
    
    def get_speed(self, vehicle_id: str) -> Optional[float]:
        """Get current speed of vehicle"""
        diagnostics = self.get_diagnostics(vehicle_id)
        return diagnostics.speed if diagnostics else None
    
    def get_fuel_level(self, vehicle_id: str) -> Optional[float]:
        """Get current fuel level of vehicle"""
        diagnostics = self.get_diagnostics(vehicle_id)
        return diagnostics.fuel_level if diagnostics else None
    
    def get_engine_health(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get engine health summary"""
        diagnostics = self.get_diagnostics(vehicle_id)
        if not diagnostics:
            return None
        
        return {
            'engine_temp': diagnostics.engine_temp,
            'oil_pressure': diagnostics.oil_pressure,
            'rpm': diagnostics.rpm,
            'engine_hours': diagnostics.engine_hours,
            'fault_codes': diagnostics.engine_fault_codes,
            'health_score': self._calculate_health_score(diagnostics)
        }
    
    def get_maintenance_alerts(self, vehicle_id: str) -> List[MaintenanceAlert]:
        """Get active maintenance alerts for vehicle"""
        try:
            alerts_key = f"telematics:alerts:{vehicle_id}"
            alert_data = self.redis_client.lrange(alerts_key, 0, -1)
            
            alerts = []
            for data in alert_data:
                alert_dict = json.loads(data.decode('utf-8'))
                alerts.append(MaintenanceAlert(
                    vehicle_id=alert_dict['vehicle_id'],
                    alert_type=alert_dict['alert_type'],
                    component=alert_dict['component'],
                    message=alert_dict['message'],
                    priority=alert_dict['priority'],
                    estimated_service_date=datetime.fromisoformat(alert_dict['estimated_service_date']) if alert_dict.get('estimated_service_date') else None,
                    mileage_threshold=alert_dict.get('mileage_threshold'),
                    created_at=datetime.fromisoformat(alert_dict['created_at'])
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get maintenance alerts for {vehicle_id}: {str(e)}")
            return []
    
    def start_monitoring(self) -> bool:
        """Start telematics monitoring"""
        try:
            if self.is_monitoring:
                return True
                
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("Telematics monitoring started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start telematics monitoring: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """Stop telematics monitoring"""
        try:
            self.is_monitoring = False
            if hasattr(self, 'monitoring_thread'):
                self.monitoring_thread.join(timeout=5)
            
            logger.info("Telematics monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring: {str(e)}")
            return False
    
    def add_diagnostic_callback(self, callback):
        """Add callback for diagnostic updates"""
        self.diagnostic_callbacks.append(callback)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                for vehicle_id in list(self.monitored_vehicles.keys()):
                    new_diagnostics = self._simulate_diagnostics_update(vehicle_id)
                    if new_diagnostics:
                        self.monitored_vehicles[vehicle_id] = new_diagnostics
                        self._store_diagnostics(new_diagnostics)
                        self._check_maintenance_alerts(new_diagnostics)
                        
                        # Trigger callbacks
                        for callback in self.diagnostic_callbacks:
                            try:
                                callback(new_diagnostics)
                            except Exception as e:
                                logger.warning(f"Diagnostic callback failed: {str(e)}")
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(5)
    
    def _simulate_diagnostics_update(self, vehicle_id: str) -> Optional[VehicleDiagnostics]:
        """Simulate diagnostic data update for demo"""
        try:
            current = self.monitored_vehicles.get(vehicle_id)
            if not current:
                return None
            
            import random
            
            # Simulate realistic changes
            new_diagnostics = VehicleDiagnostics(
                vehicle_id=vehicle_id,
                engine_temp=max(75, min(110, current.engine_temp + random.uniform(-2, 3))),
                oil_pressure=max(15, min(40, current.oil_pressure + random.uniform(-1, 1))),
                fuel_level=max(0, current.fuel_level - random.uniform(0, 2)),  # Fuel decreases
                battery_voltage=max(11, min(14, current.battery_voltage + random.uniform(-0.1, 0.1))),
                rpm=random.randint(0, 3000) if random.random() > 0.7 else 0,  # Engine running 30% of time
                speed=random.uniform(0, 80) if random.random() > 0.5 else 0,
                odometer=current.odometer + random.uniform(0, 2),  # Gradual increase
                fuel_consumption=max(5, min(15, current.fuel_consumption + random.uniform(-0.5, 0.5))),
                engine_hours=current.engine_hours + (self.monitoring_interval / 3600),
                transmission_temp=max(60, min(100, current.transmission_temp + random.uniform(-2, 2))),
                brake_pad_wear=min(100, current.brake_pad_wear + random.uniform(0, 0.1)),
                tire_pressure_fl=max(25, min(35, current.tire_pressure_fl + random.uniform(-0.5, 0.5))),
                tire_pressure_fr=max(25, min(35, current.tire_pressure_fr + random.uniform(-0.5, 0.5))),
                tire_pressure_rl=max(25, min(35, current.tire_pressure_rl + random.uniform(-0.5, 0.5))),
                tire_pressure_rr=max(25, min(35, current.tire_pressure_rr + random.uniform(-0.5, 0.5))),
                engine_fault_codes=[],  # Randomly add fault codes
                maintenance_alerts=[],
                timestamp=datetime.now()
            )
            
            # Randomly add fault codes (5% chance)
            if random.random() < 0.05:
                fault_codes = ['P0171', 'P0300', 'P0420', 'P0401', 'P0128']
                new_diagnostics.engine_fault_codes = [random.choice(fault_codes)]
            
            return new_diagnostics
            
        except Exception as e:
            logger.error(f"Failed to simulate diagnostics for {vehicle_id}: {str(e)}")
            return None
    
    def _store_diagnostics(self, diagnostics: VehicleDiagnostics):
        """Store diagnostics in Redis"""
        try:
            # Store current diagnostics
            current_key = f"telematics:diagnostics:{diagnostics.vehicle_id}"
            self.redis_client.setex(current_key, 3600, json.dumps(diagnostics.to_dict()))
            
            # Store in history
            history_key = f"telematics:history:{diagnostics.vehicle_id}"
            self.redis_client.lpush(history_key, json.dumps(diagnostics.to_dict()))
            self.redis_client.ltrim(history_key, 0, 500)  # Keep last 500 entries
            self.redis_client.expire(history_key, 86400 * 7)  # 7 days
            
        except Exception as e:
            logger.error(f"Failed to store diagnostics: {str(e)}")
    
    def _check_maintenance_alerts(self, diagnostics: VehicleDiagnostics):
        """Check for maintenance alerts based on diagnostics"""
        try:
            alerts = []
            
            # Check engine temperature
            if diagnostics.engine_temp > self.maintenance_thresholds['engine_temp']['critical']:
                alerts.append(MaintenanceAlert(
                    vehicle_id=diagnostics.vehicle_id,
                    alert_type='critical',
                    component='engine',
                    message=f'Engine overheating: {diagnostics.engine_temp}°C',
                    priority=5,
                    estimated_service_date=None,
                    mileage_threshold=None,
                    created_at=datetime.now()
                ))
            
            # Check fuel level
            if diagnostics.fuel_level < self.maintenance_thresholds['fuel_level']['warning']:
                alert_type = 'critical' if diagnostics.fuel_level < self.maintenance_thresholds['fuel_level']['critical'] else 'warning'
                priority = 5 if alert_type == 'critical' else 3
                alerts.append(MaintenanceAlert(
                    vehicle_id=diagnostics.vehicle_id,
                    alert_type=alert_type,
                    component='fuel',
                    message=f'Low fuel level: {diagnostics.fuel_level}%',
                    priority=priority,
                    estimated_service_date=None,
                    mileage_threshold=None,
                    created_at=datetime.now()
                ))
            
            # Check brake pad wear
            if diagnostics.brake_pad_wear > self.maintenance_thresholds['brake_pad_wear']['warning']:
                alert_type = 'critical' if diagnostics.brake_pad_wear > self.maintenance_thresholds['brake_pad_wear']['critical'] else 'warning'
                priority = 4 if alert_type == 'critical' else 2
                alerts.append(MaintenanceAlert(
                    vehicle_id=diagnostics.vehicle_id,
                    alert_type=alert_type,
                    component='brakes',
                    message=f'Brake pad wear: {diagnostics.brake_pad_wear}%',
                    priority=priority,
                    estimated_service_date=datetime.now() + timedelta(days=30),
                    mileage_threshold=None,
                    created_at=datetime.now()
                ))
            
            # Store alerts
            for alert in alerts:
                self._store_maintenance_alert(alert)
                
        except Exception as e:
            logger.error(f"Failed to check maintenance alerts: {str(e)}")
    
    def _store_maintenance_alert(self, alert: MaintenanceAlert):
        """Store maintenance alert"""
        try:
            alerts_key = f"telematics:alerts:{alert.vehicle_id}"
            self.redis_client.lpush(alerts_key, json.dumps(alert.to_dict()))
            self.redis_client.ltrim(alerts_key, 0, 50)  # Keep last 50 alerts
            self.redis_client.expire(alerts_key, 86400 * 30)  # 30 days
            
        except Exception as e:
            logger.error(f"Failed to store maintenance alert: {str(e)}")
    
    def _calculate_health_score(self, diagnostics: VehicleDiagnostics) -> int:
        """Calculate overall vehicle health score (0-100)"""
        try:
            score = 100
            
            # Temperature check
            if diagnostics.engine_temp > 100:
                score -= 20
            elif diagnostics.engine_temp > 95:
                score -= 10
            
            # Oil pressure check
            if diagnostics.oil_pressure < 20:
                score -= 15
            elif diagnostics.oil_pressure < 25:
                score -= 5
            
            # Fuel level (not critical for health but important)
            if diagnostics.fuel_level < 10:
                score -= 5
            
            # Brake pad wear
            if diagnostics.brake_pad_wear > 80:
                score -= 20
            elif diagnostics.brake_pad_wear > 60:
                score -= 10
            
            # Fault codes
            score -= len(diagnostics.engine_fault_codes) * 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {str(e)}")
            return 50  # Default moderate score
    
    def get_fleet_health_summary(self) -> Dict[str, Any]:
        """Get health summary for entire fleet"""
        try:
            total_vehicles = len(self.monitored_vehicles)
            if total_vehicles == 0:
                return {'total_vehicles': 0, 'avg_health_score': 0, 'critical_alerts': 0}
            
            health_scores = []
            critical_alerts = 0
            
            for vehicle_id in self.monitored_vehicles:
                diagnostics = self.get_diagnostics(vehicle_id)
                if diagnostics:
                    health_scores.append(self._calculate_health_score(diagnostics))
                    
                alerts = self.get_maintenance_alerts(vehicle_id)
                critical_alerts += sum(1 for alert in alerts if alert.priority >= 4)
            
            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
            
            return {
                'total_vehicles': total_vehicles,
                'avg_health_score': round(avg_health, 1),
                'critical_alerts': critical_alerts,
                'healthy_vehicles': sum(1 for score in health_scores if score >= 80),
                'warning_vehicles': sum(1 for score in health_scores if 60 <= score < 80),
                'critical_vehicles': sum(1 for score in health_scores if score < 60)
            }
            
        except Exception as e:
            logger.error(f"Failed to get fleet health summary: {str(e)}")
            return {'total_vehicles': 0, 'avg_health_score': 0, 'critical_alerts': 0}