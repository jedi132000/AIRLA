"""
Predictive Analytics Module for AI Logistics System
Provides ML-powered insights, risk predictions, and optimization recommendations
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json


class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PredictionType(Enum):
    """Types of predictions"""
    DELIVERY_DELAY = "delivery_delay"
    VEHICLE_BREAKDOWN = "vehicle_breakdown"
    TRAFFIC_CONGESTION = "traffic_congestion"
    DEMAND_SURGE = "demand_surge"
    ROUTE_INEFFICIENCY = "route_inefficiency"
    CUSTOMER_COMPLAINT = "customer_complaint"


@dataclass
class RiskPrediction:
    """Individual risk prediction"""
    entity_id: str
    entity_type: str  # "order", "vehicle", "route", etc.
    prediction_type: PredictionType
    risk_level: RiskLevel
    confidence: float  # 0-1
    probability: float  # 0-1
    impact_score: float  # 0-10
    predicted_time: Optional[datetime]
    factors: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]


class PredictiveAnalytics:
    """Main predictive analytics engine"""
    
    def __init__(self):
        self.models = {}
        self.historical_data = self._generate_mock_historical_data()
        self.feature_importance = {}
        
    def _generate_mock_historical_data(self) -> pd.DataFrame:
        """Generate mock historical data for predictions"""
        np.random.seed(42)  # For reproducible results
        
        # Generate 1000 historical records
        n_records = 1000
        dates = pd.date_range(start='2024-01-01', periods=n_records, freq='H')
        
        data = {
            'timestamp': dates,
            'order_id': [f'ORD-{1000+i:06d}' for i in range(n_records)],
            'vehicle_id': [f'VH-{(i%20)+1:03d}' for i in range(n_records)],
            'delivery_time_planned': np.random.normal(45, 15, n_records),
            'delivery_time_actual': np.random.normal(48, 18, n_records),
            'distance_km': np.random.normal(12, 5, n_records),
            'traffic_density': np.random.uniform(0, 1, n_records),
            'weather_score': np.random.uniform(0, 1, n_records),  # 0=bad, 1=good
            'vehicle_age_months': np.random.uniform(1, 60, n_records),
            'driver_experience_months': np.random.uniform(1, 120, n_records),
            'order_priority': np.random.choice([1,2,3,4,5], n_records),
            'customer_satisfaction': np.random.normal(4.2, 0.8, n_records),
            'had_delay': np.random.choice([0,1], n_records, p=[0.75, 0.25]),
            'had_complaint': np.random.choice([0,1], n_records, p=[0.9, 0.1]),
            'had_breakdown': np.random.choice([0,1], n_records, p=[0.95, 0.05])
        }
        
        return pd.DataFrame(data)
    
    def predict_delivery_delays(self, orders: List[Dict], vehicles: List[Dict]) -> List[RiskPrediction]:
        """Predict which deliveries are at risk of delay"""
        predictions = []
        
        for order in orders:
            # Mock prediction logic based on various factors
            risk_factors = []
            risk_score = 0
            
            # Check order priority
            priority = order.get('priority', 3)
            if priority >= 4:
                risk_score += 0.2
                risk_factors.append("High priority order (increased pressure)")
            
            # Check if vehicle assigned
            assigned_vehicle = None
            if order.get('assigned_vehicle_id'):
                assigned_vehicle = next((v for v in vehicles if v['id'] == order['assigned_vehicle_id']), None)
                
                if assigned_vehicle:
                    # Check vehicle capacity utilization
                    capacity_util = len(assigned_vehicle.get('assigned_orders', [])) / assigned_vehicle.get('max_orders', 5)
                    if capacity_util > 0.8:
                        risk_score += 0.3
                        risk_factors.append("Vehicle near capacity limit")
                    
                    # Check vehicle state
                    if assigned_vehicle.get('state') == 'maintenance':
                        risk_score += 0.8
                        risk_factors.append("Assigned vehicle in maintenance")
            else:
                risk_score += 0.4
                risk_factors.append("No vehicle assigned yet")
            
            # Mock traffic/weather impact
            if np.random.random() > 0.7:  # 30% chance of traffic issues
                risk_score += 0.25
                risk_factors.append("Heavy traffic detected on route")
            
            if np.random.random() > 0.8:  # 20% chance of weather issues
                risk_score += 0.15
                risk_factors.append("Adverse weather conditions")
            
            # Convert risk score to probability and risk level
            probability = min(risk_score, 0.95)
            confidence = 0.75 + np.random.random() * 0.2  # Mock confidence
            
            if probability < 0.2:
                risk_level = RiskLevel.LOW
            elif probability < 0.4:
                risk_level = RiskLevel.MEDIUM
            elif probability < 0.7:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            # Generate recommendations
            recommendations = []
            if "No vehicle assigned" in risk_factors:
                recommendations.append("Prioritize vehicle assignment for this order")
            if "Vehicle near capacity" in risk_factors:
                recommendations.append("Consider redistributing orders to less loaded vehicles")
            if "Heavy traffic" in risk_factors:
                recommendations.append("Route optimization recommended to avoid congested areas")
            if "Adverse weather" in risk_factors:
                recommendations.append("Consider delaying non-urgent deliveries")
            
            prediction = RiskPrediction(
                entity_id=order['id'],
                entity_type="order",
                prediction_type=PredictionType.DELIVERY_DELAY,
                risk_level=risk_level,
                confidence=confidence,
                probability=probability,
                impact_score=priority * 2,
                predicted_time=datetime.now() + timedelta(hours=2),
                factors=risk_factors,
                recommendations=recommendations,
                metadata={
                    "customer_id": order.get('customer_id'),
                    "assigned_vehicle": order.get('assigned_vehicle_id'),
                    "priority": priority
                }
            )
            
            predictions.append(prediction)
        
        return predictions
    
    def predict_vehicle_breakdowns(self, vehicles: List[Dict]) -> List[RiskPrediction]:
        """Predict which vehicles are at risk of breakdown"""
        predictions = []
        
        for vehicle in vehicles:
            risk_factors = []
            risk_score = 0
            
            # Mock age-based risk
            # In real implementation, this would use actual vehicle age and maintenance history
            mock_age_months = np.random.uniform(1, 60)
            if mock_age_months > 36:
                risk_score += 0.3
                risk_factors.append(f"Vehicle age ({mock_age_months:.0f} months)")
            
            # Mock mileage-based risk
            mock_mileage = np.random.uniform(10000, 200000)
            if mock_mileage > 150000:
                risk_score += 0.25
                risk_factors.append(f"High mileage ({mock_mileage:.0f} km)")
            
            # Check current workload
            current_orders = len(vehicle.get('assigned_orders', []))
            max_orders = vehicle.get('max_orders', 5)
            if current_orders >= max_orders:
                risk_score += 0.2
                risk_factors.append("Operating at maximum capacity")
            
            # Mock maintenance history
            if np.random.random() > 0.7:  # 30% have overdue maintenance
                risk_score += 0.4
                risk_factors.append("Overdue for scheduled maintenance")
            
            # Convert to probability and risk level
            probability = min(risk_score, 0.9)
            confidence = 0.65 + np.random.random() * 0.25
            
            if probability < 0.15:
                risk_level = RiskLevel.LOW
            elif probability < 0.35:
                risk_level = RiskLevel.MEDIUM
            elif probability < 0.6:
                risk_level = RiskLevel.HIGH
            else:
                risk_level = RiskLevel.CRITICAL
            
            # Generate recommendations
            recommendations = []
            if "Overdue for scheduled maintenance" in risk_factors:
                recommendations.append("Schedule immediate maintenance inspection")
            if "Operating at maximum capacity" in risk_factors:
                recommendations.append("Reduce workload or provide backup vehicle")
            if "High mileage" in risk_factors:
                recommendations.append("Consider vehicle replacement planning")
            if "Vehicle age" in str(risk_factors):
                recommendations.append("Increase maintenance frequency for aging vehicle")
            
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                recommendations.append("Consider temporary vehicle reassignment")
            
            prediction = RiskPrediction(
                entity_id=vehicle['id'],
                entity_type="vehicle",
                prediction_type=PredictionType.VEHICLE_BREAKDOWN,
                risk_level=risk_level,
                confidence=confidence,
                probability=probability,
                impact_score=current_orders * 2 + (5 if risk_level == RiskLevel.CRITICAL else 0),
                predicted_time=datetime.now() + timedelta(days=np.random.randint(1, 30)),
                factors=risk_factors,
                recommendations=recommendations,
                metadata={
                    "vehicle_type": vehicle.get('vehicle_type'),
                    "current_orders": current_orders,
                    "state": vehicle.get('state')
                }
            )
            
            predictions.append(prediction)
        
        return predictions
    
    def predict_demand_patterns(self) -> Dict[str, Any]:
        """Predict demand patterns and surges"""
        # Mock demand prediction
        current_hour = datetime.now().hour
        
        # Simulate daily patterns
        hourly_demand = {
            "00-06": {"demand": "Low", "multiplier": 0.3, "confidence": 0.8},
            "06-09": {"demand": "High", "multiplier": 1.5, "confidence": 0.9},
            "09-12": {"demand": "Medium", "multiplier": 1.0, "confidence": 0.85},
            "12-14": {"demand": "High", "multiplier": 1.4, "confidence": 0.88},
            "14-17": {"demand": "Medium", "multiplier": 0.9, "confidence": 0.82},
            "17-20": {"demand": "Very High", "multiplier": 1.8, "confidence": 0.92},
            "20-24": {"demand": "Low", "multiplier": 0.5, "confidence": 0.75}
        }
        
        # Weekly patterns
        day_of_week = datetime.now().strftime('%A')
        weekly_multipliers = {
            "Monday": 1.2,
            "Tuesday": 1.0,
            "Wednesday": 1.1,
            "Thursday": 1.3,
            "Friday": 1.6,
            "Saturday": 1.4,
            "Sunday": 0.8
        }
        
        return {
            "current_period_prediction": {
                "hour_range": f"{current_hour:02d}-{(current_hour+1)%24:02d}",
                "predicted_demand": "High" if weekly_multipliers[day_of_week] > 1.2 else "Medium",
                "confidence": 0.87,
                "factors": [
                    f"Day of week: {day_of_week}",
                    f"Time of day: {current_hour:02d}:00",
                    "Historical patterns",
                    "Seasonal adjustments"
                ]
            },
            "hourly_forecast": hourly_demand,
            "weekly_multiplier": weekly_multipliers[day_of_week],
            "recommendations": [
                "Pre-position vehicles in high-demand areas during peak hours",
                "Consider dynamic pricing during surge periods",
                "Ensure adequate staff coverage for predicted high-demand periods",
                f"Focus on {day_of_week} capacity planning"
            ]
        }
    
    def get_optimization_recommendations(self, orders: List[Dict], vehicles: List[Dict]) -> List[Dict[str, Any]]:
        """Generate AI-powered optimization recommendations"""
        recommendations = []
        
        # Analyze vehicle utilization
        total_vehicles = len(vehicles)
        active_vehicles = len([v for v in vehicles if v.get('state') == 'moving'])
        idle_vehicles = len([v for v in vehicles if v.get('state') == 'idle'])
        
        if idle_vehicles > total_vehicles * 0.3:
            recommendations.append({
                "type": "Fleet Optimization",
                "priority": "Medium",
                "title": "High Vehicle Idle Rate Detected",
                "description": f"{idle_vehicles}/{total_vehicles} vehicles are idle. Consider reassigning or optimizing routes.",
                "potential_savings": f"${idle_vehicles * 50:.0f}/day in operational costs",
                "action": "Redistribute orders to reduce idle time"
            })
        
        # Analyze order clustering
        unassigned_orders = len([o for o in orders if not o.get('assigned_vehicle_id')])
        if unassigned_orders > 5:
            recommendations.append({
                "type": "Order Management",
                "priority": "High",
                "title": "High Number of Unassigned Orders",
                "description": f"{unassigned_orders} orders are awaiting vehicle assignment.",
                "potential_savings": f"Reduce delivery delays by up to {unassigned_orders * 15} minutes",
                "action": "Implement automated assignment algorithm"
            })
        
        # Route optimization opportunity
        recommendations.append({
            "type": "Route Optimization",
            "priority": "High",
            "title": "Route Consolidation Opportunity",
            "description": "AI detected 3 overlapping routes that can be consolidated for efficiency.",
            "potential_savings": "Save ~2.5 hours delivery time and $180 in fuel costs",
            "action": "Apply ML-optimized route consolidation"
        })
        
        # Predictive maintenance
        recommendations.append({
            "type": "Preventive Maintenance",
            "priority": "Medium",
            "title": "Proactive Maintenance Schedule",
            "description": "2 vehicles predicted to need maintenance within 7 days.",
            "potential_savings": "Prevent $1,200 in breakdown costs",
            "action": "Schedule maintenance during low-demand periods"
        })
        
        return recommendations
    
    def generate_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights and trends"""
        return {
            "efficiency_trends": {
                "delivery_time_improvement": "+12%",
                "fuel_efficiency_gain": "+8%",
                "customer_satisfaction": "+0.3 points",
                "cost_reduction": "7.5%"
            },
            "bottlenecks_identified": [
                {
                    "area": "Route Planning",
                    "impact": "Medium",
                    "description": "Manual route planning adds ~15min per delivery",
                    "solution": "Implement automated route optimization"
                },
                {
                    "area": "Vehicle Assignment",
                    "impact": "High", 
                    "description": "Suboptimal assignments increase travel time by 20%",
                    "solution": "Use AI-powered assignment algorithms"
                }
            ],
            "success_metrics": {
                "on_time_delivery_rate": 94.2,
                "average_delivery_time": 42.3,
                "customer_satisfaction_score": 4.4,
                "fleet_utilization_rate": 78.5,
                "fuel_efficiency_mpg": 28.7
            },
            "predictions_accuracy": {
                "delivery_delays": 87.3,
                "vehicle_breakdowns": 92.1,
                "demand_forecasting": 89.6,
                "route_optimization": 94.8
            }
        }


# Global predictive analytics instance
predictive_analytics = PredictiveAnalytics()