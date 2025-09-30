"""
Sample data generator for testing the logistics system with user-friendly locations.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid
from src.models import Order, OrderState
from src.location_service import create_location_from_address

class SampleDataGenerator:
    """Generate realistic sample orders and data for testing"""
    
    # Common pickup locations (warehouses, stores, restaurants)
    PICKUP_LOCATIONS = [
        "Amazon Fulfillment Center, Staten Island, NY",
        "Best Buy, Times Square, New York, NY", 
        "Target, Herald Square, New York, NY",
        "Whole Foods, Union Square, New York, NY",
        "McDonald's, Broadway, New York, NY",
        "Starbucks, 5th Avenue, New York, NY",
        "CVS Pharmacy, Wall Street, New York, NY",
        "Home Depot, Queens, NY",
        "FedEx Office, Midtown, New York, NY",
        "Apple Store, 5th Avenue, New York, NY"
    ]
    
    # Common delivery locations (residential, offices, hotels)
    DELIVERY_LOCATIONS = [
        "Empire State Building, New York, NY",
        "Central Park West, New York, NY",
        "Brooklyn Heights, Brooklyn, NY",
        "Long Island City, Queens, NY",
        "Greenwich Village, New York, NY",
        "SoHo, New York, NY",
        "Chelsea, New York, NY",
        "Upper East Side, New York, NY",
        "Financial District, New York, NY",
        "Tribeca, New York, NY",
        "Williamsburg, Brooklyn, NY",
        "Astoria, Queens, NY",
        "Park Slope, Brooklyn, NY",
        "Hell's Kitchen, New York, NY",
        "Lower East Side, New York, NY"
    ]
    
    # Sample customer names
    CUSTOMER_NAMES = [
        "John Smith", "Emma Johnson", "Michael Brown", "Sarah Davis",
        "David Wilson", "Lisa Anderson", "James Taylor", "Jennifer Martinez",
        "Robert Garcia", "Ashley Rodriguez", "Christopher Lee", "Amanda Clark"
    ]
    
    def create_sample_order(self, order_id: str = None, priority: int = None) -> Order:
        """Create a single sample order with realistic data"""
        import random
        
        if order_id is None:
            order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
        
        if priority is None:
            priority = random.randint(1, 5)
        
        # Select random pickup and delivery locations
        pickup_address = random.choice(self.PICKUP_LOCATIONS)
        delivery_address = random.choice(self.DELIVERY_LOCATIONS)
        
        # Ensure pickup and delivery are different
        while delivery_address == pickup_address:
            delivery_address = random.choice(self.DELIVERY_LOCATIONS)
        
        # Create time window (next 2-8 hours)
        now = datetime.now()
        start_window = now + timedelta(hours=random.randint(1, 4))
        end_window = start_window + timedelta(hours=random.randint(2, 6))
        
        # Random package details
        weight = round(random.uniform(0.5, 50.0), 2)  # 0.5kg to 50kg
        volume = round(random.uniform(0.01, 2.0), 3)  # Small to medium packages
        
        # Special requirements
        special_reqs = []
        if random.random() < 0.3:  # 30% chance
            special_reqs.extend(random.sample([
                "fragile", "signature_required", "temperature_controlled", 
                "heavy_lift", "residential_delivery", "business_hours_only"
            ], random.randint(1, 2)))
        
        return Order(
            id=order_id,
            customer_id=random.choice(self.CUSTOMER_NAMES).replace(" ", "_").lower(),
            pickup_location=create_location_from_address(pickup_address),
            delivery_location=create_location_from_address(delivery_address),
            priority=priority,
            time_window_start=start_window,
            time_window_end=end_window,
            weight=weight,
            volume=volume,
            special_requirements=special_reqs
        )
    
    def create_sample_orders(self, count: int = 5) -> List[Order]:
        """Create multiple sample orders"""
        return [self.create_sample_order() for _ in range(count)]
    
    def create_urgent_order(self) -> Order:
        """Create an urgent priority order for testing"""
        return self.create_sample_order(priority=5)
    
    def create_demo_scenario(self) -> Dict[str, List[Order]]:
        """Create a complete demo scenario with different types of orders"""
        return {
            "normal_orders": self.create_sample_orders(3),
            "urgent_orders": [self.create_urgent_order(), self.create_urgent_order()],
            "bulk_orders": self.create_sample_orders(8)
        }

# Global instance
sample_generator = SampleDataGenerator()

# Convenience functions
def create_sample_order(**kwargs) -> Order:
    """Create a sample order"""
    return sample_generator.create_sample_order(**kwargs)

def create_sample_orders(count: int = 5) -> List[Order]:
    """Create multiple sample orders"""
    return sample_generator.create_sample_orders(count)

def create_demo_scenario() -> Dict[str, List[Order]]:
    """Create a demo scenario"""
    return sample_generator.create_demo_scenario()