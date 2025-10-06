"""
BLE (Bluetooth Low Energy) and NFC Integration Module

This module provides comprehensive BLE beacon and NFC tag functionality
for proximity-based package tracking and automated status updates.
"""

import json
import time
import uuid
import math
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict

from loguru import logger


class BLEBeaconType(Enum):
    """BLE beacon protocol types"""
    IBEACON = "ibeacon"
    EDDYSTONE = "eddystone"
    ALTBEACON = "altbeacon"
    CUSTOM = "custom"


class NFCTagType(Enum):
    """NFC tag types and capacities"""
    NTAG213 = "ntag213"  # 144 bytes
    NTAG215 = "ntag215"  # 504 bytes
    NTAG216 = "ntag216"  # 924 bytes
    MIFARE_CLASSIC = "mifare_classic"
    MIFARE_ULTRALIGHT = "mifare_ultralight"
    TYPE4 = "type4"


class ProximityZone(Enum):
    """Proximity zones for BLE beacons"""
    IMMEDIATE = "immediate"  # < 1 meter
    NEAR = "near"           # 1-3 meters
    FAR = "far"             # > 3 meters
    UNKNOWN = "unknown"


class NFCRecordType(Enum):
    """NFC NDEF record types"""
    TEXT = "text"
    URI = "uri"
    SMART_POSTER = "smart_poster"
    MIME = "mime"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


@dataclass
class BLEBeacon:
    """BLE beacon configuration and data"""
    uuid: str
    major: int
    minor: int
    beacon_type: BLEBeaconType
    package_id: str
    tx_power: int  # Calibrated TX power at 1m in dBm
    battery_level: float  # 0.0 to 1.0
    created_at: datetime
    last_seen: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class NFCTag:
    """NFC tag configuration and data"""
    tag_id: str
    tag_type: NFCTagType
    package_id: str
    ndef_records: List[Dict]
    capacity_bytes: int
    used_bytes: int
    is_locked: bool
    created_at: datetime
    last_read: Optional[datetime] = None
    read_count: int = 0
    write_count: int = 0
    is_active: bool = True
    
    @property
    def available_bytes(self) -> int:
        return self.capacity_bytes - self.used_bytes
    
    @property
    def usage_percentage(self) -> float:
        return (self.used_bytes / self.capacity_bytes) * 100


@dataclass
class ProximityEvent:
    """BLE proximity detection event"""
    event_id: str
    beacon_uuid: str
    package_id: str
    scanner_id: str
    rssi: int
    distance_meters: float
    proximity_zone: ProximityZone
    timestamp: datetime
    duration_seconds: Optional[float] = None
    metadata: Dict = None


@dataclass
class NFCReadEvent:
    """NFC tag read event"""
    event_id: str
    tag_id: str
    package_id: str
    reader_id: str
    records_read: List[Dict]
    read_success: bool
    timestamp: datetime
    metadata: Dict = None


class BLEBeaconManager:
    """BLE beacon management and proximity detection"""
    
    def __init__(self, scanner_id: str = None):
        self.scanner_id = scanner_id or f"BLE_SCANNER_{uuid.uuid4().hex[:8].upper()}"
        self.active_beacons: Dict[str, BLEBeacon] = {}
        self.proximity_events: List[ProximityEvent] = []
        self.scan_history: List[Dict] = []
        
        # Configuration
        self.scan_interval = 1.0  # seconds
        self.rssi_threshold = -100  # minimum RSSI to detect
        self.proximity_timeout = 30.0  # seconds before beacon considered lost
        
        logger.info(f"Initialized BLE beacon manager: {self.scanner_id}")
    
    def create_beacon(self, package_id: str, major: int = None, minor: int = None,
                     beacon_type: BLEBeaconType = BLEBeaconType.IBEACON,
                     tx_power: int = -59) -> BLEBeacon:
        """
        Create a new BLE beacon for package tracking
        
        Args:
            package_id: Package identifier
            major: Major value (auto-generated if None)
            minor: Minor value (auto-generated if None)
            beacon_type: Type of beacon protocol
            tx_power: Calibrated transmission power at 1m
        
        Returns:
            BLEBeacon object
        """
        beacon_uuid = str(uuid.uuid4())
        major = major or (hash(package_id) % 65536)
        minor = minor or int(time.time()) % 65536
        
        beacon = BLEBeacon(
            uuid=beacon_uuid,
            major=major,
            minor=minor,
            beacon_type=beacon_type,
            package_id=package_id,
            tx_power=tx_power,
            battery_level=1.0,  # Start with full battery
            created_at=datetime.now(timezone.utc),
            metadata={
                "created_by": self.scanner_id,
                "package_tracking": True,
                "auto_generated": True
            }
        )
        
        self.active_beacons[beacon_uuid] = beacon
        logger.info(f"Created BLE beacon {beacon_uuid} for package {package_id}")
        
        return beacon
    
    def simulate_beacon_scan(self, beacon_uuid: str, rssi: int = -65, 
                           scan_duration: float = 1.0) -> Dict:
        """
        Simulate scanning/detecting a BLE beacon
        
        Args:
            beacon_uuid: UUID of beacon to scan
            rssi: Received Signal Strength Indicator
            scan_duration: How long the beacon was in range
        
        Returns:
            Scan result dictionary
        """
        try:
            if beacon_uuid not in self.active_beacons:
                raise ValueError(f"Beacon {beacon_uuid} not found")
            
            beacon = self.active_beacons[beacon_uuid]
            if not beacon.is_active:
                raise ValueError(f"Beacon {beacon_uuid} is inactive")
            
            # Calculate distance from RSSI
            distance = self._calculate_distance(rssi, beacon.tx_power)
            proximity_zone = self._determine_proximity_zone(distance)
            
            # Update beacon last seen
            beacon.last_seen = datetime.now(timezone.utc)
            
            # Create proximity event
            proximity_event = ProximityEvent(
                event_id=f"PROX_{uuid.uuid4().hex[:8]}",
                beacon_uuid=beacon_uuid,
                package_id=beacon.package_id,
                scanner_id=self.scanner_id,
                rssi=rssi,
                distance_meters=round(distance, 2),
                proximity_zone=proximity_zone,
                timestamp=datetime.now(timezone.utc),
                duration_seconds=scan_duration,
                metadata={
                    "beacon_type": beacon.beacon_type.value,
                    "major": beacon.major,
                    "minor": beacon.minor,
                    "tx_power": beacon.tx_power
                }
            )
            
            self.proximity_events.append(proximity_event)
            
            scan_result = {
                "success": True,
                "beacon_uuid": beacon_uuid,
                "package_id": beacon.package_id,
                "rssi": rssi,
                "distance_meters": distance,
                "proximity_zone": proximity_zone.value,
                "scanner_id": self.scanner_id,
                "timestamp": proximity_event.timestamp,
                "beacon_info": {
                    "major": beacon.major,
                    "minor": beacon.minor,
                    "beacon_type": beacon.beacon_type.value,
                    "battery_level": beacon.battery_level
                }
            }
            
            self.scan_history.append(scan_result)
            logger.info(f"BLE beacon scan: {beacon.package_id} at {distance:.1f}m ({proximity_zone.value})")
            
            return scan_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "beacon_uuid": beacon_uuid,
                "error": str(e),
                "scanner_id": self.scanner_id,
                "timestamp": datetime.now(timezone.utc)
            }
            
            self.scan_history.append(error_result)
            logger.error(f"BLE beacon scan failed: {e}")
            
            return error_result
    
    def start_continuous_scan(self, duration_seconds: int = 60) -> List[Dict]:
        """
        Simulate continuous BLE scanning for specified duration
        
        Args:
            duration_seconds: How long to scan for
        
        Returns:
            List of detected beacons
        """
        logger.info(f"Starting continuous BLE scan for {duration_seconds} seconds")
        
        detections = []
        start_time = time.time()
        
        while (time.time() - start_time) < duration_seconds:
            # Simulate detecting random beacons
            for beacon_uuid, beacon in self.active_beacons.items():
                if beacon.is_active:
                    # Simulate varying RSSI based on movement
                    base_rssi = -65
                    rssi_variation = math.sin(time.time()) * 10  # Simulate movement
                    simulated_rssi = int(base_rssi + rssi_variation)
                    
                    if simulated_rssi > self.rssi_threshold:
                        detection = self.simulate_beacon_scan(beacon_uuid, simulated_rssi, 1.0)
                        if detection["success"]:
                            detections.append(detection)
            
            time.sleep(self.scan_interval)
        
        logger.info(f"Continuous scan completed: {len(detections)} detections")
        return detections
    
    def get_beacon_status(self, beacon_uuid: str) -> Optional[Dict]:
        """Get current status of a beacon"""
        if beacon_uuid not in self.active_beacons:
            return None
        
        beacon = self.active_beacons[beacon_uuid]
        last_seen_ago = None
        
        if beacon.last_seen:
            last_seen_ago = (datetime.now(timezone.utc) - beacon.last_seen).total_seconds()
        
        return {
            "beacon_uuid": beacon_uuid,
            "package_id": beacon.package_id,
            "is_active": beacon.is_active,
            "beacon_type": beacon.beacon_type.value,
            "battery_level": beacon.battery_level,
            "last_seen": beacon.last_seen.isoformat() if beacon.last_seen else None,
            "last_seen_seconds_ago": last_seen_ago,
            "is_online": last_seen_ago is not None and last_seen_ago < self.proximity_timeout,
            "major": beacon.major,
            "minor": beacon.minor,
            "tx_power": beacon.tx_power
        }
    
    def _calculate_distance(self, rssi: int, tx_power: int) -> float:
        """Calculate distance from RSSI using path loss model"""
        if rssi == 0:
            return -1.0
        
        ratio = tx_power - rssi
        if ratio < 0:
            return pow(10, ratio / 10.0)
        else:
            # More accurate formula for indoor environments
            accuracy = (0.89976) * pow(ratio / 41.0, 7.7095) + 0.111
            return accuracy
    
    def _determine_proximity_zone(self, distance: float) -> ProximityZone:
        """Determine proximity zone based on distance"""
        if distance < 0:
            return ProximityZone.UNKNOWN
        elif distance < 1.0:
            return ProximityZone.IMMEDIATE
        elif distance < 3.0:
            return ProximityZone.NEAR
        else:
            return ProximityZone.FAR


class NFCTagManager:
    """NFC tag management and data operations"""
    
    def __init__(self, reader_id: str = None):
        self.reader_id = reader_id or f"NFC_READER_{uuid.uuid4().hex[:8].upper()}"
        self.active_tags: Dict[str, NFCTag] = {}
        self.read_events: List[NFCReadEvent] = []
        
        # Tag capacities in bytes
        self.tag_capacities = {
            NFCTagType.NTAG213: 144,
            NFCTagType.NTAG215: 504,
            NFCTagType.NTAG216: 924,
            NFCTagType.MIFARE_ULTRALIGHT: 64,
            NFCTagType.MIFARE_CLASSIC: 1024,
            NFCTagType.TYPE4: 2048
        }
        
        logger.info(f"Initialized NFC tag manager: {self.reader_id}")
    
    def create_nfc_tag(self, package_id: str, tag_type: NFCTagType = NFCTagType.NTAG215,
                      initial_data: Dict = None) -> NFCTag:
        """
        Create a new NFC tag for package tracking
        
        Args:
            package_id: Package identifier
            tag_type: Type of NFC tag
            initial_data: Initial data to write to tag
        
        Returns:
            NFCTag object
        """
        tag_id = f"NFC_{uuid.uuid4().hex[:8].upper()}"
        capacity = self.tag_capacities[tag_type]
        
        # Create default NDEF record
        default_record = {
            "type": NFCRecordType.TEXT.value,
            "payload": json.dumps({
                "package_id": package_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "tracking_enabled": True,
                "checksum": self._calculate_checksum(package_id)
            }),
            "language": "en"
        }
        
        # Add custom data if provided
        ndef_records = [default_record]
        if initial_data:
            custom_record = {
                "type": NFCRecordType.EXTERNAL.value,
                "payload": json.dumps(initial_data),
                "domain": "logistics.tracking"
            }
            ndef_records.append(custom_record)
        
        # Calculate used bytes
        used_bytes = sum(len(json.dumps(record)) for record in ndef_records) + 32  # Header overhead
        
        tag = NFCTag(
            tag_id=tag_id,
            tag_type=tag_type,
            package_id=package_id,
            ndef_records=ndef_records,
            capacity_bytes=capacity,
            used_bytes=used_bytes,
            is_locked=False,
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_tags[tag_id] = tag
        logger.info(f"Created NFC tag {tag_id} for package {package_id} ({used_bytes}/{capacity} bytes used)")
        
        return tag
    
    def read_nfc_tag(self, tag_id: str, record_types: List[NFCRecordType] = None) -> Dict:
        """
        Simulate reading an NFC tag
        
        Args:
            tag_id: NFC tag identifier
            record_types: Specific record types to read (None = all)
        
        Returns:
            Read result dictionary
        """
        try:
            if tag_id not in self.active_tags:
                raise ValueError(f"NFC tag {tag_id} not found")
            
            tag = self.active_tags[tag_id]
            if not tag.is_active:
                raise ValueError(f"NFC tag {tag_id} is inactive")
            
            # Filter records by type if specified
            if record_types:
                record_type_values = [rt.value for rt in record_types]
                records_to_read = [r for r in tag.ndef_records if r["type"] in record_type_values]
            else:
                records_to_read = tag.ndef_records.copy()
            
            # Update tag statistics
            tag.read_count += 1
            tag.last_read = datetime.now(timezone.utc)
            
            # Create read event
            read_event = NFCReadEvent(
                event_id=f"NFC_READ_{uuid.uuid4().hex[:8]}",
                tag_id=tag_id,
                package_id=tag.package_id,
                reader_id=self.reader_id,
                records_read=records_to_read,
                read_success=True,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "tag_type": tag.tag_type.value,
                    "records_count": len(records_to_read),
                    "read_count": tag.read_count
                }
            )
            
            self.read_events.append(read_event)
            
            # Extract package data from records
            package_data = {}
            for record in records_to_read:
                try:
                    payload_data = json.loads(record["payload"])
                    package_data.update(payload_data)
                except json.JSONDecodeError:
                    package_data[record["type"]] = record["payload"]
            
            read_result = {
                "success": True,
                "tag_id": tag_id,
                "package_id": tag.package_id,
                "records": records_to_read,
                "package_data": package_data,
                "tag_info": {
                    "tag_type": tag.tag_type.value,
                    "capacity_bytes": tag.capacity_bytes,
                    "used_bytes": tag.used_bytes,
                    "read_count": tag.read_count,
                    "is_locked": tag.is_locked
                },
                "reader_id": self.reader_id,
                "timestamp": read_event.timestamp
            }
            
            logger.info(f"NFC tag read: {tag.package_id} ({len(records_to_read)} records)")
            return read_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "tag_id": tag_id,
                "error": str(e),
                "reader_id": self.reader_id,
                "timestamp": datetime.now(timezone.utc)
            }
            
            logger.error(f"NFC tag read failed: {e}")
            return error_result
    
    def write_nfc_tag(self, tag_id: str, new_records: List[Dict], 
                     append: bool = True) -> Dict:
        """
        Write new records to NFC tag
        
        Args:
            tag_id: NFC tag identifier
            new_records: New NDEF records to write
            append: Whether to append or replace existing records
        
        Returns:
            Write result dictionary
        """
        try:
            if tag_id not in self.active_tags:
                raise ValueError(f"NFC tag {tag_id} not found")
            
            tag = self.active_tags[tag_id]
            if not tag.is_active:
                raise ValueError(f"NFC tag {tag_id} is inactive")
            
            if tag.is_locked:
                raise ValueError(f"NFC tag {tag_id} is locked for writing")
            
            # Prepare new record list
            if append:
                updated_records = tag.ndef_records.copy() + new_records
            else:
                updated_records = new_records.copy()
            
            # Calculate new size
            new_size = sum(len(json.dumps(record)) for record in updated_records) + 32
            
            if new_size > tag.capacity_bytes:
                raise ValueError(f"New records exceed tag capacity ({new_size} > {tag.capacity_bytes} bytes)")
            
            # Update tag
            tag.ndef_records = updated_records
            tag.used_bytes = new_size
            tag.write_count += 1
            
            write_result = {
                "success": True,
                "tag_id": tag_id,
                "records_written": len(new_records),
                "total_records": len(updated_records),
                "bytes_used": new_size,
                "bytes_available": tag.available_bytes,
                "write_count": tag.write_count,
                "timestamp": datetime.now(timezone.utc)
            }
            
            logger.info(f"NFC tag write: {tag.package_id} ({len(new_records)} new records)")
            return write_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "tag_id": tag_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
            
            logger.error(f"NFC tag write failed: {e}")
            return error_result
    
    def get_tag_status(self, tag_id: str) -> Optional[Dict]:
        """Get current status of an NFC tag"""
        if tag_id not in self.active_tags:
            return None
        
        tag = self.active_tags[tag_id]
        
        return {
            "tag_id": tag_id,
            "package_id": tag.package_id,
            "tag_type": tag.tag_type.value,
            "is_active": tag.is_active,
            "is_locked": tag.is_locked,
            "capacity_bytes": tag.capacity_bytes,
            "used_bytes": tag.used_bytes,
            "available_bytes": tag.available_bytes,
            "usage_percentage": round(tag.usage_percentage, 1),
            "records_count": len(tag.ndef_records),
            "read_count": tag.read_count,
            "write_count": tag.write_count,
            "created_at": tag.created_at.isoformat(),
            "last_read": tag.last_read.isoformat() if tag.last_read else None
        }
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA-256 checksum for data validation"""
        return hashlib.sha256(data.encode()).hexdigest()[:8]


class BLENFCIntegrationSystem:
    """Integrated BLE and NFC system for comprehensive proximity tracking"""
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"BLE_NFC_SYS_{uuid.uuid4().hex[:8].upper()}"
        self.ble_manager = BLEBeaconManager(f"{self.system_id}_BLE")
        self.nfc_manager = NFCTagManager(f"{self.system_id}_NFC")
        
        logger.info(f"Initialized integrated BLE/NFC system: {self.system_id}")
    
    def create_package_tags(self, package_id: str, options: Dict = None) -> Dict:
        """
        Create both BLE beacon and NFC tag for a package
        
        Args:
            package_id: Package identifier
            options: Configuration options for tags
        
        Returns:
            Dictionary with created tag information
        """
        options = options or {}
        created_tags = {}
        
        # Create BLE beacon if requested
        if options.get("enable_ble", True):
            beacon = self.ble_manager.create_beacon(
                package_id=package_id,
                beacon_type=BLEBeaconType(options.get("ble_type", "ibeacon"))
            )
            created_tags["ble_beacon"] = {
                "uuid": beacon.uuid,
                "major": beacon.major,
                "minor": beacon.minor,
                "type": beacon.beacon_type.value
            }
        
        # Create NFC tag if requested
        if options.get("enable_nfc", True):
            nfc_tag = self.nfc_manager.create_nfc_tag(
                package_id=package_id,
                tag_type=NFCTagType(options.get("nfc_type", "ntag215")),
                initial_data=options.get("nfc_data")
            )
            created_tags["nfc_tag"] = {
                "tag_id": nfc_tag.tag_id,
                "type": nfc_tag.tag_type.value,
                "capacity": nfc_tag.capacity_bytes,
                "records": len(nfc_tag.ndef_records)
            }
        
        logger.info(f"Created package tags for {package_id}: {list(created_tags.keys())}")
        return {
            "package_id": package_id,
            "tags": created_tags,
            "system_id": self.system_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def simulate_proximity_detection(self, package_id: str, detection_type: str = "both") -> List[Dict]:
        """
        Simulate detecting a package via BLE and/or NFC
        
        Args:
            package_id: Package to detect
            detection_type: "ble", "nfc", or "both"
        
        Returns:
            List of detection events
        """
        detections = []
        
        if detection_type in ["ble", "both"]:
            # Find BLE beacon for package
            for beacon_uuid, beacon in self.ble_manager.active_beacons.items():
                if beacon.package_id == package_id:
                    ble_result = self.ble_manager.simulate_beacon_scan(beacon_uuid)
                    if ble_result["success"]:
                        detections.append({
                            "detection_type": "ble_proximity",
                            "package_id": package_id,
                            "result": ble_result
                        })
                    break
        
        if detection_type in ["nfc", "both"]:
            # Find NFC tag for package
            for tag_id, tag in self.nfc_manager.active_tags.items():
                if tag.package_id == package_id:
                    nfc_result = self.nfc_manager.read_nfc_tag(tag_id)
                    if nfc_result["success"]:
                        detections.append({
                            "detection_type": "nfc_read",
                            "package_id": package_id,
                            "result": nfc_result
                        })
                    break
        
        return detections
    
    def get_system_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        ble_beacons = len(self.ble_manager.active_beacons)
        nfc_tags = len(self.nfc_manager.active_tags)
        
        # BLE statistics
        ble_active = sum(1 for b in self.ble_manager.active_beacons.values() if b.is_active)
        ble_detections = len(self.ble_manager.proximity_events)
        
        # NFC statistics
        nfc_active = sum(1 for t in self.nfc_manager.active_tags.values() if t.is_active)
        nfc_reads = len(self.nfc_manager.read_events)
        
        return {
            "system_id": self.system_id,
            "ble_beacons": {
                "total": ble_beacons,
                "active": ble_active,
                "detections": ble_detections
            },
            "nfc_tags": {
                "total": nfc_tags,
                "active": nfc_active,
                "reads": nfc_reads
            },
            "total_devices": ble_beacons + nfc_tags,
            "total_interactions": ble_detections + nfc_reads
        }


if __name__ == "__main__":
    # Demo usage
    system = BLENFCIntegrationSystem()
    
    # Create tags for demo package
    package_tags = system.create_package_tags("PKG_DEMO_BLE_NFC_001")
    
    # Simulate detections
    detections = system.simulate_proximity_detection("PKG_DEMO_BLE_NFC_001")
    
    # Print statistics
    stats = system.get_system_statistics()
    print("BLE/NFC System Statistics:", json.dumps(stats, indent=2))