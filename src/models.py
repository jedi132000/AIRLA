"""
Core data models for the logistics routing system.
Defines the node types, states, and data structures.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OrderState(str, Enum):
    """Order lifecycle states"""
    NEW = "new"
    ASSIGNED = "assigned" 
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    FAILED = "failed"


class VehicleState(str, Enum):
    """Vehicle operational states"""
    IDLE = "idle"
    ASSIGNED = "assigned"
    MOVING = "moving"
    MAINTENANCE = "maintenance"


class AgentState(str, Enum):
    """Agent coordination states"""
    PLANNING = "planning"
    EXECUTING = "executing"
    REASSIGNING = "reassigning"
    MONITORING = "monitoring"


class MessageType(str, Enum):
    """Message types for agent communication"""
    ORDER_UPDATE = "order_update"
    VEHICLE_UPDATE = "vehicle_update"
    ROUTE_UPDATE = "route_update"
    SYSTEM_ALERT = "system_alert"
    COORDINATION_REQUEST = "coordination_request"
    STATUS_REPORT = "status_report"
    NEW_ORDER_CREATED = "new_order_created"
    ORDER_ASSIGNED = "order_assigned"
    DELIVERY_COMPLETED = "delivery_completed"
    EMERGENCY_ALERT = "emergency_alert"


class Location(BaseModel):
    """Geographic location model - user-friendly with address-first approach"""
    address: str  # Primary field - human readable address
    latitude: Optional[float] = None  # Auto-populated via geocoding
    longitude: Optional[float] = None  # Auto-populated via geocoding
    location_id: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "USA"
    postal_code: Optional[str] = None
    
    def __str__(self) -> str:
        return self.address
    
    @property
    def coordinates(self) -> Optional[tuple[float, float]]:
        """Get coordinates as (lat, lng) tuple if available"""
        if self.latitude is not None and self.longitude is not None:
            return (self.latitude, self.longitude)
        return None
    
    @property
    def has_coordinates(self) -> bool:
        """Check if location has valid coordinates"""
        return self.latitude is not None and self.longitude is not None


class Order(BaseModel):
    """Delivery order node"""
    id: str
    customer_id: str
    pickup_location: Location
    delivery_location: Location
    priority: int = Field(default=1, ge=1, le=5)  # 1=low, 5=urgent
    time_window_start: Optional[datetime] = None
    time_window_end: Optional[datetime] = None
    weight: float = 0.0  # kg
    volume: float = 0.0  # cubic meters
    state: OrderState = OrderState.NEW
    created_at: datetime = Field(default_factory=datetime.now)
    special_requirements: List[str] = Field(default_factory=list)


class Vehicle(BaseModel):
    """Vehicle node"""
    id: str
    driver_id: Optional[str] = None
    vehicle_type: str = "van"  # van, truck, bike, drone
    capacity_weight: float = 1000.0  # kg
    capacity_volume: float = 5.0  # cubic meters
    current_location: Location
    state: VehicleState = VehicleState.IDLE
    assigned_orders: List[str] = Field(default_factory=list)
    max_orders: int = 10


class Route(BaseModel):
    """Route information between locations"""
    start_location: Location
    end_location: Location
    distance_km: float
    estimated_duration_minutes: int
    traffic_factor: float = 1.0
    waypoints: List[Location] = Field(default_factory=list)


class AgentMessage(BaseModel):
    """Inter-agent communication message"""
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemState(BaseModel):
    """Global system state"""
    orders: Dict[str, Order] = Field(default_factory=dict)
    vehicles: Dict[str, Vehicle] = Field(default_factory=dict)
    routes: Dict[str, Route] = Field(default_factory=dict)
    agent_states: Dict[str, AgentState] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def update_timestamp(self):
        """Update the last modified timestamp"""
        self.last_updated = datetime.now()


class TrafficData(BaseModel):
    """Real-time traffic information"""
    location: Location
    congestion_level: float = Field(ge=0.0, le=1.0)  # 0=clear, 1=heavy
    average_speed_kmh: float
    last_updated: datetime = Field(default_factory=datetime.now)


class WeatherData(BaseModel):
    """Weather conditions affecting delivery"""
    location: Location
    condition: str  # clear, rain, snow, storm
    temperature_celsius: float
    wind_speed_kmh: float
    visibility_km: float
    impact_factor: float = Field(ge=0.0, le=2.0)  # 0=no impact, 2=severe


class AgentMessage(BaseModel):
    """Message for inter-agent communication"""
    id: str
    sender_agent: str
    recipient_agent: Optional[str] = None  # None for broadcast
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    priority: int = Field(default=1, ge=1, le=5)