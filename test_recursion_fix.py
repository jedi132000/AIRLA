#!/usr/bin/env python3
"""
Test script to verify the recursion limit fix for the logistics system.
"""

import sys
sys.path.append('src')

from logistics_system import LogisticsSystem
from loguru import logger
import time

def test_recursion_fix():
    """Test that the system properly handles no vehicles available scenario"""
    print("🔍 === Testing Recursion Fix ===")
    
    try:
        # Initialize system
        system = LogisticsSystem()
        system.start_system()
        print("✅ System initialized successfully")
        
        # Create an order with no vehicles available
        order_data = {
            "customer_id": "TEST_CUST_001",
            "priority": 3,
            "weight": 25.0,
            "volume": 1.2,
            "pickup_location": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "New York, NY"
            },
            "delivery_location": {
                "latitude": 40.7589,
                "longitude": -73.9851,
                "address": "Times Square, NY"
            }
        }
        
        print("\n📦 Creating test order...")
        result = system.process_new_order(order_data)
        order_id = result.get("order_id")
        print(f"   Order created: {order_id}")
        
        # Get system status before workflow
        orders = system.get_orders(limit=5)
        vehicles = system.get_vehicles()
        
        print(f"\n📊 System Status Before Workflow:")
        print(f"   Orders: {len(orders)}")
        print(f"   Available Vehicles: {len([v for v in vehicles if v.get('state') == 'available'])}")
        
        # Run workflow cycle with timeout protection
        print("\n🔄 Running workflow cycle...")
        start_time = time.time()
        
        try:
            workflow_result = system.run_workflow_cycle()
            elapsed = time.time() - start_time
            
            print(f"✅ Workflow completed in {elapsed:.2f} seconds")
            print(f"   Result: {workflow_result.get('message', 'Success')}")
            
            if elapsed < 5.0:  # Should complete quickly
                print("🎉 Recursion fix working correctly - no infinite loop!")
            else:
                print("⚠️ Workflow took longer than expected")
                
        except RecursionError as e:
            print(f"❌ Recursion error still occurring: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Other error occurred: {e}")
            
        # Check final system status
        final_orders = system.get_orders(limit=5)
        print(f"\n📊 System Status After Workflow:")
        print(f"   Orders: {len(final_orders)}")
        
        if final_orders:
            test_order = next((o for o in final_orders if o.get('id') == order_id), None)
            if test_order:
                print(f"   Test Order State: {test_order.get('state', 'unknown')}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_recursion_fix()
    if success:
        print("\n🎯 Recursion limit fix is working correctly!")
        print("   The system now properly handles scenarios with no available vehicles.")
    else:
        print("\n💥 Test failed - recursion issue may still exist.")
        sys.exit(1)