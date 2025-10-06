"""
Package Tracking System with QR/Barcode and BLE/NFC Integration

This module provides comprehensive package tracking capabilities including:
- QR code and barcode scanning for status updates
- BLE (Bluetooth Low Energy) and NFC tag integration
- Real-time package journey tracking
- Automated checkpoint updates
- Integration with carrier APIs
"""

import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import hashlib
import base64

from loguru import logger

# Import scanning and integration modules
try:
    from .barcode_scanner import BarcodeScanner, BarcodeFormat, ScannerCapability
    from .ble_nfc_integration import BLENFCIntegrationSystem, BLEBeaconType, NFCTagType
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from barcode_scanner import BarcodeScanner, BarcodeFormat, ScannerCapability
    from ble_nfc_integration import BLENFCIntegrationSystem, BLEBeaconType, NFCTagType


class PackageStatus(Enum):
    """Package status enumeration"""
    CREATED = "created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    AT_FACILITY = "at_facility"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"


class ScanType(Enum):
    """Scanning method enumeration"""
    QR_CODE = "qr_code"
    BARCODE = "barcode"
    BLE_TAG = "ble_tag"
    NFC_TAG = "nfc_tag"
    RFID = "rfid"
    MANUAL = "manual"


class TagType(Enum):
    """Tag technology enumeration"""
    BLE_BEACON = "ble_beacon"
    NFC_TAG = "nfc_tag"
    RFID_TAG = "rfid_tag"
    QR_CODE = "qr_code"
    BARCODE_128 = "code128"
    BARCODE_39 = "code39"


@dataclass
class PackageTag:
    """Package tracking tag information"""
    tag_id: str
    tag_type: TagType
    package_id: str
    created_at: datetime
    data: Dict
    is_active: bool = True
    last_scanned: Optional[datetime] = None
    scan_count: int = 0


@dataclass
class ScanEvent:
    """Package scan event data"""
    event_id: str
    package_id: str
    tag_id: str
    scan_type: ScanType
    scanner_id: str
    location: Dict
    timestamp: datetime
    status: PackageStatus
    metadata: Dict
    signature: Optional[str] = None


@dataclass
class PackageJourney:
    """Complete package tracking journey"""
    package_id: str
    tracking_number: str
    order_id: str
    created_at: datetime
    status: PackageStatus
    events: List[ScanEvent]
    tags: List[PackageTag]
    current_location: Optional[Dict] = None
    estimated_delivery: Optional[datetime] = None
    delivery_confirmation: Optional[Dict] = None


# Legacy compatibility - now uses enhanced BarcodeScanner
class QRBarcodeScanner:
    """Legacy QR Code and Barcode scanning functionality - now uses enhanced BarcodeScanner"""
    
    def __init__(self):
        self.scanner_id = f"SCANNER_{uuid.uuid4().hex[:8].upper()}"
        self.enhanced_scanner = BarcodeScanner(self.scanner_id)
        logger.info(f"Initialized enhanced QR/Barcode scanner: {self.scanner_id}")
    
    def generate_qr_code(self, package_id: str, data: Dict) -> str:
        """Generate QR code data for package"""
        qr_info = self.enhanced_scanner.generate_qr_code({
            "package_id": package_id,
            "tracking_number": data.get("tracking_number"),
            "order_id": data.get("order_id")
        })
        
        logger.debug(f"Generated enhanced QR code for package {package_id}")
        return qr_info["qr_code"]
    
    def generate_barcode(self, package_id: str, barcode_type: str = "code128") -> str:
        """Generate barcode for package"""
        format_map = {
            "code128": BarcodeFormat.CODE128,
            "code39": BarcodeFormat.CODE39,
            "ean13": BarcodeFormat.EAN13
        }
        
        barcode_format = format_map.get(barcode_type, BarcodeFormat.CODE128)
        barcode_info = self.enhanced_scanner.generate_barcode(package_id, barcode_format)
        
        logger.debug(f"Generated enhanced {barcode_type} barcode for package {package_id}")
        return barcode_info["barcode"]
    
    def scan_qr_code(self, qr_data: str) -> Dict:
        """Simulate QR code scanning using enhanced scanner"""
        scan_result = self.enhanced_scanner.scan_qr_code(qr_data)
        
        # Convert to legacy format for compatibility
        if scan_result["success"]:
            logger.info(f"Successfully scanned QR code for package {scan_result['data'].get('package_id', 'unknown')}")
            return {
                "success": True,
                "scan_type": ScanType.QR_CODE,
                "data": scan_result["data"],
                "scanner_id": self.scanner_id,
                "timestamp": scan_result["timestamp"],
                "quality_score": scan_result.get("quality_score", 100)
            }
        else:
            logger.error(f"Enhanced QR code scan failed: {scan_result['error']}")
            return {
                "success": False,
                "error": scan_result["error"],
                "scanner_id": self.scanner_id,
                "timestamp": scan_result["timestamp"]
            }
    
    def scan_barcode(self, barcode_data: str) -> Dict:
        """Simulate barcode scanning using enhanced scanner"""
        scan_result = self.enhanced_scanner.scan_barcode(barcode_data)
        
        # Convert to legacy format for compatibility
        if scan_result["success"]:
            logger.info(f"Successfully scanned barcode for package {scan_result['package_id']}")
            return {
                "success": True,
                "scan_type": ScanType.BARCODE,
                "data": {"package_id": scan_result["package_id"]},
                "scanner_id": self.scanner_id,
                "timestamp": scan_result["timestamp"],
                "format": scan_result["format"],
                "quality_score": scan_result.get("quality_score", 100)
            }
        else:
            logger.error(f"Enhanced barcode scan failed: {scan_result['error']}")
            return {
                "success": False,
                "error": scan_result["error"],
                "scanner_id": self.scanner_id,
                "timestamp": scan_result["timestamp"]
            }
    
    def _generate_checksum(self, data: str) -> str:
        """Generate checksum for data validation"""
        return hashlib.md5(data.encode()).hexdigest()


# Legacy compatibility - now uses enhanced BLENFCIntegrationSystem
class BLENFCIntegration:
    """Legacy Bluetooth Low Energy and NFC integration - now uses enhanced system"""
    
    def __init__(self):
        self.device_id = f"BLE_NFC_{uuid.uuid4().hex[:8].upper()}"
        self.enhanced_system = BLENFCIntegrationSystem(self.device_id)
        self.active_beacons = self.enhanced_system.ble_manager.active_beacons
        self.nfc_tags = self.enhanced_system.nfc_manager.active_tags
        logger.info(f"Initialized enhanced BLE/NFC integration: {self.device_id}")
    
    def create_ble_beacon(self, package_id: str, major: int = 1, minor: int = 1) -> Dict:
        """Create BLE beacon for package tracking using enhanced system"""
        beacon = self.enhanced_system.ble_manager.create_beacon(
            package_id=package_id,
            major=major,
            minor=minor
        )
        
        beacon_data = {
            "uuid": beacon.uuid,
            "major": beacon.major,
            "minor": beacon.minor,
            "package_id": beacon.package_id,
            "tx_power": beacon.tx_power,
            "created_at": beacon.created_at,
            "is_active": beacon.is_active
        }
        
        logger.info(f"Created enhanced BLE beacon {beacon.uuid} for package {package_id}")
        return beacon_data
    
    def create_nfc_tag(self, package_id: str, tag_type: str = "NTAG213") -> Dict:
        """Create NFC tag for package tracking using enhanced system"""
        # Map legacy tag types to new enum
        tag_type_map = {
            "NTAG213": NFCTagType.NTAG213,
            "NTAG215": NFCTagType.NTAG215,
            "NTAG216": NFCTagType.NTAG216
        }
        
        nfc_tag_type = tag_type_map.get(tag_type, NFCTagType.NTAG213)
        nfc_tag = self.enhanced_system.nfc_manager.create_nfc_tag(
            package_id=package_id,
            tag_type=nfc_tag_type
        )
        
        nfc_data = {
            "tag_id": nfc_tag.tag_id,
            "tag_type": nfc_tag.tag_type.value,
            "package_id": nfc_tag.package_id,
            "ndef_record": nfc_tag.ndef_records[0] if nfc_tag.ndef_records else {},
            "created_at": nfc_tag.created_at,
            "is_active": nfc_tag.is_active,
            "read_count": nfc_tag.read_count
        }
        
        logger.info(f"Created enhanced NFC tag {nfc_tag.tag_id} for package {package_id}")
        return nfc_data
    
    def scan_ble_beacon(self, beacon_uuid: str, rssi: int = -65) -> Dict:
        """Simulate BLE beacon scanning using enhanced system"""
        scan_result = self.enhanced_system.ble_manager.simulate_beacon_scan(beacon_uuid, rssi)
        
        # Convert to legacy format for compatibility
        if scan_result["success"]:
            logger.info(f"Successfully scanned BLE beacon for package {scan_result['package_id']}")
            return {
                "success": True,
                "scan_type": ScanType.BLE_TAG,
                "beacon_uuid": beacon_uuid,
                "package_id": scan_result["package_id"],
                "rssi": scan_result["rssi"],
                "distance_meters": scan_result["distance_meters"],
                "major": scan_result["beacon_info"]["major"],
                "minor": scan_result["beacon_info"]["minor"],
                "scanner_id": self.device_id,
                "timestamp": scan_result["timestamp"],
                "proximity_zone": scan_result["proximity_zone"]
            }
        else:
            logger.error(f"Enhanced BLE beacon scan failed: {scan_result['error']}")
            return {
                "success": False,
                "error": scan_result["error"],
                "scanner_id": self.device_id,
                "timestamp": scan_result["timestamp"]
            }
    
    def scan_nfc_tag(self, tag_id: str) -> Dict:
        """Simulate NFC tag scanning using enhanced system"""
        scan_result = self.enhanced_system.nfc_manager.read_nfc_tag(tag_id)
        
        # Convert to legacy format for compatibility
        if scan_result["success"]:
            logger.info(f"Successfully scanned NFC tag for package {scan_result['package_id']}")
            return {
                "success": True,
                "scan_type": ScanType.NFC_TAG,
                "tag_id": tag_id,
                "tag_type": scan_result["tag_info"]["tag_type"],
                "package_id": scan_result["package_id"],
                "read_count": scan_result["tag_info"]["read_count"],
                "scanner_id": self.device_id,
                "timestamp": scan_result["timestamp"],
                "package_data": scan_result["package_data"]
            }
        else:
            logger.error(f"Enhanced NFC tag scan failed: {scan_result['error']}")
            return {
                "success": False,
                "error": scan_result["error"],
                "scanner_id": self.device_id,
                "timestamp": scan_result["timestamp"]
            }
    
    def _calculate_distance_from_rssi(self, rssi: int, tx_power: int) -> float:
        """Calculate approximate distance from RSSI"""
        if rssi == 0:
            return -1.0
        
        ratio = tx_power - rssi
        if ratio < 0:
            return pow(10, ratio / 10.0)
        else:
            accuracy = (0.89976) * pow(ratio / 41.0, 7.7095) + 0.111
            return accuracy
    
    def _generate_nfc_checksum(self, data: str) -> str:
        """Generate NFC checksum"""
        return hashlib.sha256(data.encode()).hexdigest()[:8]


class PackageTrackingSystem:
    """Comprehensive package tracking system"""
    
    def __init__(self, state_manager=None):
        self.state_manager = state_manager
        self.qr_scanner = QRBarcodeScanner()
        self.ble_nfc = BLENFCIntegration()
        self.packages = {}
        self.scan_events = []
        logger.info("Initialized Package Tracking System")
    
    def create_package_tracking(self, package_id: str, order_id: str, 
                              tracking_options: Optional[Dict] = None) -> PackageJourney:
        """Create comprehensive package tracking"""
        tracking_number = f"PKG_{package_id}_{int(time.time())}"
        
        # Create package journey
        journey = PackageJourney(
            package_id=package_id,
            tracking_number=tracking_number,
            order_id=order_id,
            created_at=datetime.now(timezone.utc),
            status=PackageStatus.CREATED,
            events=[],
            tags=[]
        )
        
        # Create tracking tags based on options
        options = tracking_options or {}
        
        if options.get("enable_qr", True):
            qr_code = self.qr_scanner.generate_qr_code(package_id, {
                "tracking_number": tracking_number,
                "order_id": order_id
            })
            
            qr_tag = PackageTag(
                tag_id=f"QR_{package_id}",
                tag_type=TagType.QR_CODE,
                package_id=package_id,
                created_at=datetime.now(timezone.utc),
                data={"qr_code": qr_code}
            )
            journey.tags.append(qr_tag)
        
        if options.get("enable_barcode", True):
            barcode = self.qr_scanner.generate_barcode(package_id)
            
            barcode_tag = PackageTag(
                tag_id=f"BC_{package_id}",
                tag_type=TagType.BARCODE_128,
                package_id=package_id,
                created_at=datetime.now(timezone.utc),
                data={"barcode": barcode}
            )
            journey.tags.append(barcode_tag)
        
        if options.get("enable_ble", False):
            beacon_data = self.ble_nfc.create_ble_beacon(package_id)
            
            ble_tag = PackageTag(
                tag_id=beacon_data["uuid"],
                tag_type=TagType.BLE_BEACON,
                package_id=package_id,
                created_at=datetime.now(timezone.utc),
                data=beacon_data
            )
            journey.tags.append(ble_tag)
        
        if options.get("enable_nfc", False):
            nfc_data = self.ble_nfc.create_nfc_tag(package_id)
            
            nfc_tag = PackageTag(
                tag_id=nfc_data["tag_id"],
                tag_type=TagType.NFC_TAG,
                package_id=package_id,
                created_at=datetime.now(timezone.utc),
                data=nfc_data
            )
            journey.tags.append(nfc_tag)
        
        self.packages[package_id] = journey
        
        # Create initial scan event
        initial_event = ScanEvent(
            event_id=f"EVT_{uuid.uuid4().hex[:8]}",
            package_id=package_id,
            tag_id="SYSTEM",
            scan_type=ScanType.MANUAL,
            scanner_id="SYSTEM",
            location={"type": "system", "name": "Package Created"},
            timestamp=datetime.now(timezone.utc),
            status=PackageStatus.CREATED,
            metadata={"tracking_number": tracking_number, "order_id": order_id}
        )
        
        journey.events.append(initial_event)
        self.scan_events.append(initial_event)
        
        logger.info(f"Created package tracking for {package_id} with {len(journey.tags)} tags")
        return journey
    
    def process_scan_event(self, scan_data: Dict, location: Dict, 
                          new_status: Optional[PackageStatus] = None) -> Dict:
        """Process a scan event and update package status"""
        try:
            if not scan_data.get("success"):
                return {"success": False, "error": "Invalid scan data"}
            
            # Try to get package_id from data field first, then from root level
            package_id = None
            if "data" in scan_data and isinstance(scan_data["data"], dict):
                package_id = scan_data["data"].get("package_id")
            if not package_id:
                package_id = scan_data.get("package_id")
                
            if not package_id or package_id not in self.packages:
                return {"success": False, "error": "Package not found"}
            
            journey = self.packages[package_id]
            
            # Determine new status
            if not new_status:
                new_status = self._determine_status_from_location(location)
            
            # Create scan event
            event = ScanEvent(
                event_id=f"EVT_{uuid.uuid4().hex[:8]}",
                package_id=package_id,
                tag_id=scan_data.get("tag_id", "UNKNOWN"),
                scan_type=scan_data["scan_type"],
                scanner_id=scan_data["scanner_id"],
                location=location,
                timestamp=scan_data["timestamp"],
                status=new_status,
                metadata=scan_data.copy()
            )
            
            # Update package journey
            journey.events.append(event)
            journey.status = new_status
            journey.current_location = location
            
            # Update tag scan count
            for tag in journey.tags:
                if tag.tag_id == scan_data.get("tag_id"):
                    tag.last_scanned = scan_data["timestamp"]
                    tag.scan_count += 1
                    break
            
            self.scan_events.append(event)
            
            logger.info(f"Processed scan event for package {package_id}: {new_status.value}")
            
            return {
                "success": True,
                "event_id": event.event_id,
                "package_id": package_id,
                "status": new_status.value,
                "location": location,
                "timestamp": event.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process scan event: {e}")
            return {"success": False, "error": str(e)}
    
    def get_package_journey(self, package_id: str) -> Optional[Dict]:
        """Get complete package tracking journey"""
        if package_id not in self.packages:
            return None
        
        journey = self.packages[package_id]
        return {
            "package_id": journey.package_id,
            "tracking_number": journey.tracking_number,
            "order_id": journey.order_id,
            "status": journey.status.value,
            "created_at": journey.created_at.isoformat(),
            "current_location": journey.current_location,
            "events": [
                {
                    "event_id": event.event_id,
                    "scan_type": event.scan_type.value,
                    "scanner_id": event.scanner_id,
                    "location": event.location,
                    "timestamp": event.timestamp.isoformat(),
                    "status": event.status.value,
                    "metadata": event.metadata
                }
                for event in journey.events
            ],
            "tags": [
                {
                    "tag_id": tag.tag_id,
                    "tag_type": tag.tag_type.value,
                    "is_active": tag.is_active,
                    "scan_count": tag.scan_count,
                    "last_scanned": tag.last_scanned.isoformat() if tag.last_scanned else None
                }
                for tag in journey.tags
            ]
        }
    
    def simulate_package_scan(self, package_id: str, scan_type: str = "qr_code", 
                             location: Optional[Dict] = None) -> Dict:
        """Simulate scanning a package at a checkpoint"""
        if package_id not in self.packages:
            return {"success": False, "error": "Package not found"}
        
        journey = self.packages[package_id]
        location = location or {"type": "checkpoint", "name": "Automated Scan"}
        
        # Find appropriate tag
        tag = None
        if scan_type == "qr_code":
            tag = next((t for t in journey.tags if t.tag_type == TagType.QR_CODE), None)
        elif scan_type == "barcode":
            tag = next((t for t in journey.tags if t.tag_type == TagType.BARCODE_128), None)
        elif scan_type == "ble":
            tag = next((t for t in journey.tags if t.tag_type == TagType.BLE_BEACON), None)
        elif scan_type == "nfc":
            tag = next((t for t in journey.tags if t.tag_type == TagType.NFC_TAG), None)
        
        if not tag:
            return {"success": False, "error": f"No {scan_type} tag found for package"}
        
        # Simulate scan based on type
        if scan_type == "qr_code":
            scan_result = self.qr_scanner.scan_qr_code(tag.data["qr_code"])
        elif scan_type == "barcode":
            scan_result = self.qr_scanner.scan_barcode(tag.data["barcode"])
        elif scan_type == "ble":
            scan_result = self.ble_nfc.scan_ble_beacon(tag.tag_id)
        elif scan_type == "nfc":
            scan_result = self.ble_nfc.scan_nfc_tag(tag.tag_id)
        else:
            return {"success": False, "error": "Invalid scan type"}
        
        if not scan_result.get("success"):
            return scan_result
        
        # Process the scan event
        return self.process_scan_event(scan_result, location)
    
    def _determine_status_from_location(self, location: Dict) -> PackageStatus:
        """Determine package status based on location type"""
        location_type = location.get("type", "").lower()
        location_name = location.get("name", "").lower()
        
        if "pickup" in location_name or "origin" in location_name:
            return PackageStatus.PICKED_UP
        elif "delivery" in location_name or "destination" in location_name:
            return PackageStatus.OUT_FOR_DELIVERY
        elif "facility" in location_type or "hub" in location_name:
            return PackageStatus.AT_FACILITY
        elif "vehicle" in location_type or "truck" in location_name:
            return PackageStatus.IN_TRANSIT
        else:
            return PackageStatus.IN_TRANSIT
    
    def get_scanning_statistics(self) -> Dict:
        """Get package scanning statistics"""
        total_packages = len(self.packages)
        total_scans = len(self.scan_events)
        
        scan_types = {}
        status_counts = {}
        
        for event in self.scan_events:
            scan_type = event.scan_type.value
            status = event.status.value
            
            scan_types[scan_type] = scan_types.get(scan_type, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
        
        active_tags = 0
        for journey in self.packages.values():
            active_tags += sum(1 for tag in journey.tags if tag.is_active)
        
        return {
            "total_packages": total_packages,
            "total_scans": total_scans,
            "active_tags": active_tags,
            "scan_types": scan_types,
            "status_distribution": status_counts,
            "average_scans_per_package": round(total_scans / max(total_packages, 1), 2)
        }


# Demo and testing functionality
def create_demo_package_tracking():
    """Create demo package tracking data"""
    tracker = PackageTrackingSystem()
    
    # Create demo packages
    demo_packages = [
        {
            "package_id": "PKG_DEMO_001",
            "order_id": "ORD_20251005_001",
            "options": {"enable_qr": True, "enable_barcode": True, "enable_ble": True}
        },
        {
            "package_id": "PKG_DEMO_002", 
            "order_id": "ORD_20251005_002",
            "options": {"enable_qr": True, "enable_nfc": True}
        },
        {
            "package_id": "PKG_DEMO_003",
            "order_id": "ORD_20251005_003", 
            "options": {"enable_barcode": True, "enable_ble": True, "enable_nfc": True}
        }
    ]
    
    for pkg in demo_packages:
        journey = tracker.create_package_tracking(
            pkg["package_id"], 
            pkg["order_id"], 
            pkg["options"]
        )
        
        # Simulate some scan events
        locations = [
            {"type": "facility", "name": "Origin Hub", "address": "123 Main St"},
            {"type": "vehicle", "name": "Delivery Truck VEH_001"},
            {"type": "facility", "name": "Destination Hub", "address": "456 Oak Ave"},
            {"type": "delivery", "name": "Customer Location", "address": "789 Pine Rd"}
        ]
        
        for i, location in enumerate(locations):
            if i < 2:  # Only simulate first 2 checkpoints
                result = tracker.simulate_package_scan(
                    pkg["package_id"], 
                    "qr_code", 
                    location
                )
                logger.info(f"Demo scan result: {result}")
    
    return tracker


if __name__ == "__main__":
    # Run demo
    demo_tracker = create_demo_package_tracking()
    stats = demo_tracker.get_scanning_statistics()
    print("📦 Package Tracking Demo Statistics:")
    print(json.dumps(stats, indent=2))