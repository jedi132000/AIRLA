"""
Demo script for Package Tracking System with QR/Barcode and BLE/NFC Integration

This script demonstrates the complete package tracking functionality including:
- QR code and barcode generation/scanning
- BLE beacon proximity detection
- NFC tag read/write operations
- Package journey tracking
- Batch scanning operations
"""

import sys
import os
import time
import json
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from tracking.package_tracker import PackageTrackingSystem, PackageStatus, ScanType, create_demo_package_tracking
    from tracking.barcode_scanner import BarcodeScanner, BarcodeFormat
    from tracking.ble_nfc_integration import BLENFCIntegrationSystem, BLEBeaconType, NFCTagType
    print("✅ Successfully imported all package tracking modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def demo_qr_barcode_scanning():
    """Demonstrate QR code and barcode functionality"""
    print("\n🏷️ === QR Code & Barcode Demo ===")
    
    scanner = BarcodeScanner()
    
    # Generate QR code
    qr_info = scanner.generate_qr_code({
        "package_id": "PKG_DEMO_QR_001",
        "order_id": "ORD_QR_001",
        "customer": "Demo Customer"
    })
    
    print(f"📱 Generated QR Code: {qr_info['qr_code'][:50]}...")
    print(f"   Size: {qr_info['size_bytes']} bytes")
    print(f"   Error Correction: {qr_info['error_correction']}")
    
    # Generate barcode
    barcode_info = scanner.generate_barcode("PKG_DEMO_BC_001", BarcodeFormat.CODE128)
    print(f"🏷️ Generated Barcode: {barcode_info['barcode']}")
    print(f"   Format: {barcode_info['format']}")
    print(f"   Length: {barcode_info['length']} characters")
    
    # Scan QR code
    qr_scan_result = scanner.scan_qr_code(qr_info['qr_code'])
    if qr_scan_result['success']:
        print(f"✅ QR Scan Success: Package {qr_scan_result['data']['package_id']}")
        print(f"   Quality Score: {qr_scan_result['quality_score']:.1f}%")
    
    # Scan barcode
    barcode_scan_result = scanner.scan_barcode(barcode_info['barcode'])
    if barcode_scan_result['success']:
        print(f"✅ Barcode Scan Success: Package {barcode_scan_result['package_id']}")
        print(f"   Format: {barcode_scan_result['format']}")
    
    # Demonstrate batch scanning
    print("\n📊 Batch Scanning Demo:")
    batch_data = [
        {"data": qr_info['qr_code'], "type": "qr_code"},
        {"data": barcode_info['barcode'], "type": "barcode"}
    ]
    
    batch_results = scanner.batch_scan(batch_data)
    successful_scans = sum(1 for r in batch_results if r.get('success'))
    print(f"   Processed {len(batch_results)} codes, {successful_scans} successful")
    
    # Scanner statistics
    stats = scanner.get_scanner_statistics()
    print(f"\n📈 Scanner Statistics:")
    print(f"   Total Scans: {stats['total_scans']}")
    print(f"   Success Rate: {stats['success_rate']}%")
    print(f"   Avg Scan Time: {stats['average_scan_time_ms']:.1f}ms")


def demo_ble_nfc_integration():
    """Demonstrate BLE beacon and NFC tag functionality"""
    print("\n📡 === BLE & NFC Integration Demo ===")
    
    system = BLENFCIntegrationSystem()
    
    # Create package tags
    package_tags = system.create_package_tags("PKG_DEMO_BLE_NFC_001", {
        "enable_ble": True,
        "enable_nfc": True,
        "ble_type": "ibeacon",
        "nfc_type": "ntag215"
    })
    
    print(f"📦 Created tags for package: {package_tags['package_id']}")
    
    # BLE beacon demonstration
    if "ble_beacon" in package_tags["tags"]:
        beacon_uuid = package_tags["tags"]["ble_beacon"]["uuid"]
        print(f"🔵 BLE Beacon: {beacon_uuid}")
        
        # Simulate proximity detection at different distances
        rssi_values = [-50, -65, -80, -95]  # Different distances
        for rssi in rssi_values:
            scan_result = system.ble_manager.simulate_beacon_scan(beacon_uuid, rssi)
            if scan_result["success"]:
                print(f"   RSSI {rssi}dBm: {scan_result['distance_meters']:.1f}m ({scan_result['proximity_zone']})")
    
    # NFC tag demonstration
    if "nfc_tag" in package_tags["tags"]:
        tag_id = package_tags["tags"]["nfc_tag"]["tag_id"]
        print(f"🏷️ NFC Tag: {tag_id}")
        
        # Read NFC tag
        read_result = system.nfc_manager.read_nfc_tag(tag_id)
        if read_result["success"]:
            print(f"   Read Success: {read_result['package_id']}")
            print(f"   Records: {len(read_result['records'])}")
            print(f"   Capacity: {read_result['tag_info']['capacity_bytes']} bytes")
        
        # Write additional data to NFC tag
        new_record = {
            "type": "external",
            "payload": json.dumps({
                "scan_timestamp": datetime.now().isoformat(),
                "location": "Demo Facility",
                "operator": "Demo Operator"
            }),
            "domain": "demo.logistics"
        }
        
        write_result = system.nfc_manager.write_nfc_tag(tag_id, [new_record])
        if write_result["success"]:
            print(f"   Write Success: {write_result['records_written']} new records")
    
    # System statistics
    stats = system.get_system_statistics()
    print(f"\n📈 BLE/NFC System Statistics:")
    print(f"   BLE Beacons: {stats['ble_beacons']['total']} ({stats['ble_beacons']['active']} active)")
    print(f"   NFC Tags: {stats['nfc_tags']['total']} ({stats['nfc_tags']['active']} active)")
    print(f"   Total Interactions: {stats['total_interactions']}")


def demo_package_journey_tracking():
    """Demonstrate complete package journey tracking"""
    print("\n🛣️ === Package Journey Tracking Demo ===")
    
    tracker = PackageTrackingSystem()
    
    # Create comprehensive package tracking
    journey = tracker.create_package_tracking(
        "PKG_JOURNEY_001",
        "ORD_JOURNEY_001", 
        {
            "enable_qr": True,
            "enable_barcode": True,
            "enable_ble": True,
            "enable_nfc": True
        }
    )
    
    print(f"📦 Created tracking for: {journey.package_id}")
    print(f"   Tracking Number: {journey.tracking_number}")
    print(f"   Tags Created: {len(journey.tags)}")
    
    # Simulate package journey
    checkpoints = [
        {"name": "Origin Hub", "type": "facility", "scan_type": "qr_code"},
        {"name": "Sorting Center", "type": "facility", "scan_type": "barcode"},
        {"name": "Delivery Truck", "type": "vehicle", "scan_type": "ble"},
        {"name": "Customer Location", "type": "delivery", "scan_type": "nfc"}
    ]
    
    print(f"\n📍 Package Journey Simulation:")
    for i, checkpoint in enumerate(checkpoints, 1):
        print(f"   Step {i}: {checkpoint['name']} ({checkpoint['scan_type']})")
        
        # Simulate scan at checkpoint
        result = tracker.simulate_package_scan(
            journey.package_id,
            checkpoint['scan_type'],
            checkpoint
        )
        
        if result["success"]:
            print(f"     ✅ Scan successful")
        else:
            print(f"     ❌ Scan failed: {result['error']}")
        
        time.sleep(0.5)  # Simulate time between checkpoints
    
    # Get complete journey
    journey_data = tracker.get_package_journey(journey.package_id)
    if journey_data:
        print(f"\n📊 Journey Summary:")
        print(f"   Current Status: {journey_data['status']}")
        print(f"   Total Events: {len(journey_data['events'])}")
        print(f"   Current Location: {journey_data.get('current_location', {}).get('name', 'Unknown')}")
        
        # Show event timeline
        print(f"   Event Timeline:")
        for event in journey_data['events']:
            timestamp = datetime.fromisoformat(event['timestamp']).strftime("%H:%M:%S")
            print(f"     {timestamp}: {event['status']} ({event['scan_type']})")
    
    # Tracking statistics
    stats = tracker.get_scanning_statistics()
    print(f"\n📈 Tracking Statistics:")
    print(f"   Total Packages: {stats['total_packages']}")
    print(f"   Total Scans: {stats['total_scans']}")
    print(f"   Active Tags: {stats['active_tags']}")
    print(f"   Avg Scans/Package: {stats['average_scans_per_package']}")


def demo_integration_with_logistics_system():
    """Demonstrate integration with the main logistics system"""
    print("\n🔗 === Logistics System Integration Demo ===")
    
    try:
        from logistics_system import LogisticsSystem
        
        # Initialize main logistics system
        logistics_system = LogisticsSystem()
        logistics_system.start_system()
        
        # Initialize package tracking
        package_tracker = PackageTrackingSystem()
        
        print("✅ Both systems initialized successfully")
        
        # Create order in logistics system
        order_data = {
            "customer_id": "CUST_INTEGRATION_001",
            "priority": 2,
            "weight": 15.0,
            "volume": 1.0,
            "pickup_location": {
                "address": "123 Pickup Street",
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "delivery_location": {
                "address": "456 Delivery Avenue", 
                "latitude": 40.7589,
                "longitude": -73.9851
            }
        }
        
        # Process order
        order_result = logistics_system.process_new_order(order_data)
        order_id = order_result.get("order_id")
        
        if order_id:
            print(f"📦 Created order: {order_id}")
            
            # Create package tracking for the order
            package_id = f"PKG_{order_id}"
            journey = package_tracker.create_package_tracking(
                package_id,
                order_id,
                {"enable_qr": True, "enable_barcode": True}
            )
            
            print(f"🏷️ Created package tracking: {journey.tracking_number}")
            
            # Run logistics workflow
            workflow_result = logistics_system.run_workflow_cycle()
            if not workflow_result.get('workflow_result', {}).get('failed'):
                print("✅ Logistics workflow completed successfully")
                
                # Simulate package scan after processing
                scan_result = package_tracker.simulate_package_scan(
                    package_id,
                    "qr_code",
                    {"name": "Automated Processing", "type": "system"}
                )
                
                if scan_result["success"]:
                    print("📱 Package scan integrated with workflow")
            
            # Get system status
            system_status = logistics_system.get_system_status()
            print(f"\n📊 System Integration Status:")
            print(f"   Orders: {len(logistics_system.get_orders())} total")
            print(f"   Vehicles: {len(logistics_system.get_vehicles())} total") 
            print(f"   Packages: {len(package_tracker.packages)} tracked")
        
    except ImportError:
        print("⚠️ Main logistics system not available for integration demo")
    except Exception as e:
        print(f"❌ Integration error: {e}")


def main():
    """Run all package tracking demos"""
    print("🚀 === Package Tracking System Demo ===")
    print("This demo showcases the complete QR/Barcode scanning and BLE/NFC integration features.\n")
    
    try:
        # Run individual demos
        demo_qr_barcode_scanning()
        demo_ble_nfc_integration()  
        demo_package_journey_tracking()
        demo_integration_with_logistics_system()
        
        print("\n🎉 === Demo Complete ===")
        print("✅ All package tracking features demonstrated successfully!")
        print("\n💡 Next Steps:")
        print("- Run the dashboard: python -m streamlit run dashboard.py")
        print("- Access Package Tracking tab in the dashboard")
        print("- Explore real-time scanning and tracking features")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()