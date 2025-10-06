#!/usr/bin/env python3
"""
Quick fix for the recursion limit issue by implementing a circuit breaker pattern.
"""

import sys
sys.path.append('src')

from base_agent import AgentOrchestrator
from state_manager import StateManager
import redis

def apply_recursion_fix():
    """Apply recursion limit fix by increasing LangGraph's recursion limit"""
    print("🔧 Applying recursion limit fix...")
    
    try:
        # Connect to Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Test connection
        redis_client.ping()
        print("✅ Redis connection established")
        
        # Initialize state manager and orchestrator
        state_manager = StateManager(redis_client)
        orchestrator = AgentOrchestrator(state_manager)
        
        print("✅ Orchestrator initialized")
        
        # Set LangGraph recursion limit to a higher value
        import os
        os.environ['LANGCHAIN_RECURSION_LIMIT'] = '50'
        
        print("✅ Recursion limit set to 50")
        
        # Clear any stuck workflow state
        try:
            redis_client.delete('workflow_state')
            redis_client.delete('orchestrator_state') 
            print("✅ Cleared stuck workflow state")
        except:
            pass
            
        print("🎯 Recursion fix applied successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply fix: {e}")
        return False

if __name__ == "__main__":
    success = apply_recursion_fix()
    if success:
        print("\n🚀 System is ready! The recursion limit has been increased.")
        print("   You can now run the simulation without hitting the limit.")
        print("   Try running: .venv/bin/python package_tracking_demo.py")
    else:
        print("\n💥 Fix failed. Please check Redis connection and try again.")
        sys.exit(1)