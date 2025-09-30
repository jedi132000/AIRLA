#!/usr/bin/env python3
"""
Main entry point for the logistics system.
Can be run directly to start the system or used as a module.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from logistics_system import LogisticsSystem
from loguru import logger


def main():
    """Main function to run the logistics system"""
    logger.info("Starting AI-Powered Logistics System...")
    
    try:
        # Initialize and start system
        system = LogisticsSystem()
        system.start_system()
        
        logger.info("System started successfully!")
        logger.info("Run 'streamlit run dashboard.py' to access the web interface")
        
        # Keep system running
        import time
        while True:
            try:
                # Run periodic workflow cycles
                result = system.run_workflow_cycle()
                logger.info(f"Workflow cycle completed: {result.get('workflow_result', {}).get('timestamp', 'unknown')}")
                
                # Wait before next cycle
                time.sleep(60)  # 1 minute intervals
                
            except KeyboardInterrupt:
                logger.info("Shutting down system...")
                system.stop_system()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    except Exception as e:
        logger.error(f"Failed to start system: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()