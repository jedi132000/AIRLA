"""
Geocoding utilities for converting addresses to coordinates and vice versa.
Provides user-friendly location handling for the logistics system.
"""
from typing import Optional, Dict, Any
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from src.models import Location

logger = logging.getLogger(__name__)

class LocationService:
    """Service for handling location geocoding and address resolution"""
    
    def __init__(self):
        # Use Nominatim (OpenStreetMap) as it's free and doesn't require API keys
        self.geocoder = Nominatim(user_agent="ai_logistics_system", timeout=10)
    
    def geocode_address(self, address: str) -> Optional[tuple[float, float]]:
        """
        Convert a human-readable address to coordinates.
        
        Args:
            address: Human-readable address (e.g., "123 Main St, New York, NY")
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            location = self.geocoder.geocode(address)
            if location:
                logger.info(f"Geocoded '{address}' to ({location.latitude}, {location.longitude})")
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"Could not geocode address: {address}")
                return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding error for '{address}': {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Convert coordinates to a human-readable address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Human-readable address string or None if reverse geocoding fails
        """
        try:
            location = self.geocoder.reverse((latitude, longitude))
            if location:
                address = location.address
                logger.info(f"Reverse geocoded ({latitude}, {longitude}) to '{address}'")
                return address
            else:
                logger.warning(f"Could not reverse geocode coordinates: ({latitude}, {longitude})")
                return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Reverse geocoding error for ({latitude}, {longitude}): {e}")
            return None
    
    def create_location_from_address(self, address: str, **kwargs) -> Location:
        """
        Create a Location object from an address, automatically geocoding coordinates.
        
        Args:
            address: Human-readable address
            **kwargs: Additional location fields (city, country, postal_code, etc.)
            
        Returns:
            Location object with geocoded coordinates
        """
        # Try to geocode the address
        coords = self.geocode_address(address)
        
        location_data = {
            "address": address,
            **kwargs
        }
        
        if coords:
            location_data["latitude"] = coords[0]
            location_data["longitude"] = coords[1]
        
        return Location(**location_data)
    
    def create_location_from_coordinates(self, latitude: float, longitude: float, **kwargs) -> Location:
        """
        Create a Location object from coordinates, automatically reverse geocoding address.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            **kwargs: Additional location fields
            
        Returns:
            Location object with reverse geocoded address
        """
        # Try to reverse geocode the coordinates
        address = self.reverse_geocode(latitude, longitude)
        
        location_data = {
            "latitude": latitude,
            "longitude": longitude,
            "address": address or f"Coordinates: {latitude}, {longitude}",
            **kwargs
        }
        
        return Location(**location_data)
    
    def validate_and_enrich_location(self, location: Location) -> Location:
        """
        Validate and enrich a location object by filling missing data.
        
        Args:
            location: Location object to validate and enrich
            
        Returns:
            Enriched Location object
        """
        # If we have address but no coordinates, try geocoding
        if location.address and not location.has_coordinates:
            coords = self.geocode_address(location.address)
            if coords:
                location.latitude = coords[0]
                location.longitude = coords[1]
        
        # If we have coordinates but no address, try reverse geocoding
        elif location.has_coordinates and not location.address:
            address = self.reverse_geocode(location.latitude, location.longitude)
            if address:
                location.address = address
        
        return location

# Global instance for easy access
location_service = LocationService()

# Convenience functions
def create_location_from_address(address: str, **kwargs) -> Location:
    """Create a Location from a human-readable address"""
    return location_service.create_location_from_address(address, **kwargs)

def create_location_from_coordinates(lat: float, lng: float, **kwargs) -> Location:
    """Create a Location from coordinates"""
    return location_service.create_location_from_coordinates(lat, lng, **kwargs)

def get_sample_locations():
    """Get common location examples for testing/demo (lazy-loaded)"""
    return {
        "warehouse": create_location_from_address("1600 Amphitheatre Parkway, Mountain View, CA"),
        "downtown_sf": create_location_from_address("Union Square, San Francisco, CA"),
        "airport": create_location_from_address("San Francisco International Airport, CA"),
        "office": create_location_from_address("123 Market Street, San Francisco, CA"),
        "home": create_location_from_address("456 Oak Street, San Francisco, CA")
    }