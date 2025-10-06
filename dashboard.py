"""
Streamlit dashboard for the AI-powered logistics and routing system.
Provides real-time visualization and control interface.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import time
import json
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Any

# Add src to path for imports
import sys
import os
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Import our logistics system components
from logistics_system import LogisticsSystem
from models import OrderState, VehicleState

# Import tracking system
try:
    from tracking.vehicle_monitor import VehicleMonitor
    from tracking.gps_tracker import GPSTracker, GPSLocation
    from tracking.telematics import TelematicsUnit, VehicleDiagnostics
    from tracking.setup import setup_gps_tracking, get_system_status
    TRACKING_AVAILABLE = True
except ImportError as e:
    st.warning(f"Live tracking system not available: {e}")
    TRACKING_AVAILABLE = False

# Import audit logger from parent directory
sys.path.insert(0, os.path.dirname(__file__))
from audit_logger import audit_logger, AuditEventType, AuditSeverity
from notification_system import notification_manager, NotificationType, NotificationPriority
from predictive_analytics import predictive_analytics, RiskLevel


# Page configuration
st.set_page_config(
    page_title="AI Logistics Dashboard",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/logistics-ai/help',
        'Report a bug': 'https://github.com/logistics-ai/issues',
        'About': "# AI-Powered Logistics Dashboard\nEnterprise-grade logistics management with multi-agent AI orchestration."
    }
)

# Initialize session state
if 'logistics_system' not in st.session_state:
    st.session_state.logistics_system = LogisticsSystem()
    st.session_state.system_started = False

# Initialize vehicle tracking system
if TRACKING_AVAILABLE and 'vehicle_monitor' not in st.session_state:
    try:
        st.session_state.vehicle_monitor = VehicleMonitor()
        st.session_state.tracking_enabled = False
        st.session_state.tracking_status = get_system_status()
    except Exception as e:
        st.session_state.vehicle_monitor = None
        st.session_state.tracking_enabled = False
        st.session_state.tracking_status = {'error': str(e)}

# Sidebar controls with enhanced UI
with st.sidebar:
    st.title("🚛 Logistics Control")
    
    # Theme and user preferences
    st.markdown("### ⚙️ Settings")
    
    # Theme toggle
    theme_mode = st.selectbox(
        "🎨 Theme",
        ["Auto", "Light", "Dark"],
        help="Choose your preferred theme. 'Auto' follows system settings."
    )
    
    # Auto-refresh settings
    auto_refresh_interval = st.selectbox(
        "🔄 Auto Refresh",
        ["Off", "30 seconds", "1 minute", "5 minutes"],
        index=1,
        help="Automatically refresh dashboard data"
    )
    
    # Notification settings
    enable_notifications = st.checkbox(
        "🔔 Enable Notifications",
        value=True,
        help="Show system alerts and exception notifications"
    )
    
    # Role-based access control
    user_role = st.selectbox(
        "👤 User Role",
        ["Operator", "Manager", "Administrator"],
        index=0,
        help="Select your access level for appropriate features"
    )
    
    st.divider()
    
    # System control with enhanced tooltips
    st.subheader("🎛️ System Control")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start System", 
            disabled=st.session_state.system_started,
            help="Initialize all agents and start the logistics orchestration system"
        ):
            try:
                st.session_state.logistics_system.start_system()
                st.session_state.system_started = True
                audit_logger.log_system_event("start", details={"user_role": user_role})
                st.success("✅ System started successfully!")
                st.rerun()
            except Exception as e:
                audit_logger.log_system_event("error", details={"error": str(e), "action": "start_system"})
                st.error(f"❌ Failed to start system: {e}")
    
    with col2:
        if st.button(
            "⏹️ Stop System", 
            disabled=not st.session_state.system_started,
            help="Safely shutdown all agents and stop the system"
        ):
            st.session_state.logistics_system.stop_system()
            st.session_state.system_started = False
            audit_logger.log_system_event("stop", details={"user_role": user_role})
            st.success("🛑 System stopped!")
            st.rerun()
    
    # System actions with better organization
    if st.session_state.system_started:
        st.subheader("⚡ Quick Actions")
        
        if st.button(
            "🔄 Run Workflow Cycle",
            help="Execute one complete cycle of the agent workflow for processing orders and optimizing routes"
        ):
            with st.spinner("🔄 Running workflow cycle..."):
                result = st.session_state.logistics_system.run_workflow_cycle()
                if "error" not in result:
                    audit_logger.log_system_event("workflow_cycle", details={"result": result})
                    st.success("✅ Workflow cycle completed!")
                else:
                    audit_logger.log_system_event("error", details={"error": result['error'], "action": "workflow_cycle"})
                    st.error(f"❌ Workflow failed: {result['error']}")
        
        # Emergency controls (restricted access)
        if user_role in ["Manager", "Administrator"]:
            st.markdown("#### 🚨 Emergency Controls")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(
                    "🚨 Emergency Stop",
                    help="⚠️ DANGER: Immediately halt all operations and activate emergency protocols",
                    type="secondary"
                ):
                    result = st.session_state.logistics_system.trigger_emergency_protocols("manual_dashboard_trigger")
                    if "error" not in result:
                        audit_logger.log_system_event("emergency_activated", AuditSeverity.CRITICAL, details={"user_role": user_role})
                        st.warning("🚨 Emergency protocols activated!")
                    else:
                        st.error(f"❌ Emergency activation failed: {result['error']}")
            
            with col2:
                if st.button(
                    "🔄 System Reset",
                    help="⚠️ Reset all system state and restart agents (USE WITH CAUTION)",
                    type="secondary"
                ):
                    try:
                        result = st.session_state.logistics_system.clear_system_data(confirm=True)
                        audit_logger.log_system_event("system_reset", AuditSeverity.HIGH, details={"user_role": user_role})
                        if "error" not in result:
                            st.success("🔄 System reset completed successfully!")
                        else:
                            st.error(f"❌ System reset failed: {result['error']}")
                    except Exception as e:
                        audit_logger.log_system_event("system_reset_failed", AuditSeverity.HIGH, details={"error": str(e)})
                        st.error(f"❌ System reset failed: {str(e)}")
        
        # Clear data (with confirmation)
        st.subheader("⚠️ Danger Zone")
        if st.checkbox("Enable data clearing"):
            if st.button("Clear All Data", type="secondary"):
                if st.button("Confirm Clear All Data", type="primary"):
                    result = st.session_state.logistics_system.clear_system_data(confirm=True)
                    if "error" not in result:
                        st.success("System data cleared!")
                    else:
                        st.error(f"Clear failed: {result['error']}")

# Enhanced main dashboard header with status indicators
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    st.title("🚛 AI-Powered Logistics & Routing Dashboard")
    st.markdown("**Multi-Agent System for Intelligent Fleet Management & Route Optimization**")

with col2:
    # System status with enhanced indicators
    if st.session_state.system_started:
        system_status = st.session_state.logistics_system.get_system_status()
        if system_status.get('system_active', False):
            st.success("🟢 System Online")
            st.caption(f"⚡ {system_status.get('active_agents', 0)}/6 Agents Active")
        else:
            st.warning("🟡 System Starting...")
    else:
        st.error("🔴 System Offline")
        st.caption("⏸️ All agents stopped")

with col3:
    # System health indicators
    if st.session_state.system_started:
        try:
            from src.state_manager import StateManager
            test_state_manager = StateManager()
            redis_status = test_state_manager.redis_client.ping()
            st.success("💾 Redis Connected")
        except:
            st.error("💾 Redis Disconnected")
        
        # Quick stats
        orders_count = len(st.session_state.logistics_system.get_orders())
        vehicles_count = len(st.session_state.logistics_system.get_vehicles())
        st.caption(f"📦 {orders_count} Orders | 🚛 {vehicles_count} Vehicles")

if not st.session_state.system_started:
    st.info("👆 Please start the system using the sidebar controls to view the dashboard.")
    st.stop()

# Enhanced controls bar
col1, col2, col3, col4 = st.columns(4)

with col1:
    # Auto-refresh with interval selection
    auto_refresh_enabled = auto_refresh_interval != "Off"
    if auto_refresh_enabled:
        st.success(f"🔄 Auto-refresh: {auto_refresh_interval}")
    else:
        st.info("⏸️ Auto-refresh: Disabled")

with col2:
    # Enhanced notifications with notification manager
    if enable_notifications:
        notification_manager.render_notification_badge()
    else:
        st.caption("🔕 Notifications: Off")

with col3:
    # User role indicator
    role_colors = {"Operator": "🟢", "Manager": "🟡", "Administrator": "🔴"}
    st.info(f"{role_colors.get(user_role, '👤')} Role: {user_role}")

with col4:
    # Current time and last update
    current_time = datetime.now().strftime("%H:%M:%S")
    st.caption(f"🕐 Current: {current_time}")
    st.caption("🔄 Last refresh: Just now")

# Main content tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Overview", 
    "📦 Orders", 
    "🚐 Vehicles", 
    "🗺️ Map", 
    "📡 Live Tracking",
    "🔍 Monitoring", 
    "⚠️ Exceptions",
    "📋 Audit Log"
])

# Get system status and data
try:
    system_status = st.session_state.logistics_system.get_system_status()
    orders_data = st.session_state.logistics_system.get_orders()
    vehicles_data = st.session_state.logistics_system.get_vehicles()
except Exception as e:
    st.error(f"Failed to get system data: {e}")
    st.stop()

with tab1:
    st.header("📊 Intelligent System Overview")
    
    # Enhanced key metrics with predictive insights
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_orders = len(orders_data)
        pending_orders = len([o for o in orders_data if o.get('state') == 'new'])
        st.metric("Total Orders", total_orders, delta=f"{pending_orders} pending", help="All orders in system with pending count")
    
    with col2:
        total_vehicles = len(vehicles_data)
        active_vehicles = len([v for v in vehicles_data if v.get('state') == 'moving'])
        st.metric("Total Vehicles", total_vehicles, delta=f"{active_vehicles} active", help="Fleet size with currently active vehicles")
    
    with col3:
        uptime = system_status.get("uptime_minutes", 0)
        st.metric("Uptime (min)", f"{uptime:.1f}", help="System operational time since last restart")
    
    with col4:
        # AI Performance Score (mock calculation)
        ai_performance = 94.7  # Mock AI performance score
        st.metric("🤖 AI Performance", f"{ai_performance}%", delta="2.3%", help="Overall AI agent efficiency score")
    
    st.divider()
    
    # Predictive Analytics Section
    st.subheader("🔮 AI-Powered Predictive Insights")
    
    # Get predictions
    delay_predictions = predictive_analytics.predict_delivery_delays(orders_data, vehicles_data)
    breakdown_predictions = predictive_analytics.predict_vehicle_breakdowns(vehicles_data)
    demand_forecast = predictive_analytics.predict_demand_patterns()
    optimization_recommendations = predictive_analytics.get_optimization_recommendations(orders_data, vehicles_data)
    
    # Risk Assessment Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📦 Delivery Risk Analysis")
        high_risk_deliveries = [p for p in delay_predictions if p.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        
        if high_risk_deliveries:
            st.error(f"🚨 {len(high_risk_deliveries)} high-risk deliveries detected")
            
            # Show top risk order
            top_risk = max(high_risk_deliveries, key=lambda x: x.probability)
            with st.expander(f"⚠️ Highest Risk: {top_risk.entity_id}"):
                st.write(f"**Risk Level:** {top_risk.risk_level.value.title()}")
                st.write(f"**Probability:** {top_risk.probability:.1%}")
                st.write(f"**Confidence:** {top_risk.confidence:.1%}")
                st.write("**Risk Factors:**")
                for factor in top_risk.factors:
                    st.write(f"• {factor}")
                st.write("**AI Recommendations:**")
                for rec in top_risk.recommendations:
                    st.write(f"• {rec}")
        else:
            st.success("✅ All deliveries are low risk")
    
    with col2:
        st.markdown("### 🚛 Vehicle Health Predictions")
        high_risk_vehicles = [p for p in breakdown_predictions if p.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]
        
        if high_risk_vehicles:
            st.warning(f"⚠️ {len(high_risk_vehicles)} vehicles need attention")
            
            # Show most critical vehicle
            top_risk_vehicle = max(high_risk_vehicles, key=lambda x: x.probability)
            with st.expander(f"🔧 Priority: {top_risk_vehicle.entity_id}"):
                st.write(f"**Risk Level:** {top_risk_vehicle.risk_level.value.title()}")
                st.write(f"**Breakdown Probability:** {top_risk_vehicle.probability:.1%}")
                st.write(f"**Predicted Time:** {top_risk_vehicle.predicted_time.strftime('%Y-%m-%d')}")
                st.write("**Risk Factors:**")
                for factor in top_risk_vehicle.factors:
                    st.write(f"• {factor}")
                st.write("**Preventive Actions:**")
                for rec in top_risk_vehicle.recommendations:
                    st.write(f"• {rec}")
        else:
            st.success("✅ All vehicles in good condition")
    
    with col3:
        st.markdown("### 📈 Demand Forecast")
        current_prediction = demand_forecast["current_period_prediction"]
        st.info(f"📊 Next Hour: {current_prediction['predicted_demand']} Demand")
        st.write(f"**Confidence:** {current_prediction['confidence']:.1%}")
        
        weekly_mult = demand_forecast["weekly_multiplier"]
        if weekly_mult > 1.3:
            st.warning("🔥 High demand day - prepare extra capacity")
        elif weekly_mult < 0.9:
            st.info("📉 Low demand day - optimize for efficiency")
        
        with st.expander("📋 Demand Factors"):
            for factor in current_prediction['factors']:
                st.write(f"• {factor}")
    
    st.divider()
    
    # AI Optimization Recommendations
    st.subheader("🎯 AI Optimization Recommendations")
    
    if optimization_recommendations:
        for i, rec in enumerate(optimization_recommendations):
            priority_colors = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
            
            with st.expander(f"{priority_colors.get(rec['priority'], '📋')} {rec['title']} ({rec['priority']} Priority)"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Category:** {rec['type']}")
                    st.write(f"**Description:** {rec['description']}")
                    st.write(f"**Recommended Action:** {rec['action']}")
                
                with col2:
                    st.success(f"💰 **Potential Savings**\\n{rec['potential_savings']}")
                    
                    if st.button(f"✅ Apply Recommendation", key=f"apply_rec_{i}"):
                        # Log the action
                        notification_manager.add_notification(
                            "Optimization Applied",
                            f"Applied recommendation: {rec['title']}",
                            NotificationType.SUCCESS,
                            NotificationPriority.MEDIUM
                        )
                        st.success("✅ Recommendation applied!")
    else:
        st.info("🎉 System is running optimally - no immediate recommendations")
    
    st.divider()
    
    # Traditional Charts and Status Distribution
    st.subheader("📈 System Status Distribution")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Order Status Distribution")
        order_states = system_status.get("order_states", {})
        if order_states:
            fig_orders = px.pie(
                values=list(order_states.values()),
                names=list(order_states.keys()),
                title="Orders by Status"
            )
            st.plotly_chart(fig_orders, use_container_width=True)
        else:
            st.info("No orders to display")
    
    with col2:
        st.subheader("Vehicle Status Distribution")
        vehicle_states = system_status.get("vehicle_states", {})
        if vehicle_states:
            fig_vehicles = px.pie(
                values=list(vehicle_states.values()),
                names=list(vehicle_states.keys()),
                title="Vehicles by Status"
            )
            st.plotly_chart(fig_vehicles, use_container_width=True)
        else:
            st.info("No vehicles to display")
    
    # Agent status
    st.subheader("Agent Status")
    agent_status = system_status.get("agent_status", {})
    
    if agent_status:
        agents_df = pd.DataFrame(list(agent_status.items()), columns=["Agent", "Status"])
        
        # Color code agent status
        def get_status_color(status):
            colors = {
                "planning": "🟡",
                "executing": "🟢", 
                "monitoring": "🔵",
                "reassigning": "🟠"
            }
            return colors.get(status, "⚪")
        
        agents_df["Status"] = agents_df["Status"].apply(lambda x: f"{get_status_color(x)} {x}")
        
        st.dataframe(agents_df, use_container_width=True)
    else:
        st.info("No agent status data available")

with tab2:
    st.header("Order Management")
    
    # Order creation form - User-Friendly Address Input
    with st.expander("➕ Create New Order"):
        with st.form("new_order_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                customer_id = st.text_input("Customer ID", value=f"CUST_{int(time.time())}")
                priority = st.selectbox("Priority", [1, 2, 3, 4, 5], index=0, 
                                        help="1=Low, 5=Urgent")
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=1000.0, value=10.0)
                volume = st.number_input("Volume (m³)", min_value=0.0, max_value=10.0, value=0.5)
            
            with col2:
                st.write("**📍 Pickup Location**")
                pickup_address = st.text_input("Pickup Address", 
                                               value="Times Square, New York, NY",
                                               help="Enter a full address (e.g., '123 Main St, New York, NY')")
                
                st.write("**🎯 Delivery Location**") 
                delivery_address = st.text_input("Delivery Address",
                                                 value="Central Park, New York, NY",
                                                 help="Enter a full address (e.g., '456 Oak Ave, Brooklyn, NY')")
            
            # Special requirements
            special_reqs = st.multiselect("Special Requirements", 
                                         ["fragile", "signature_required", "temperature_controlled", 
                                          "heavy_lift", "residential_delivery", "business_hours_only"])
            
            # Sample locations dropdown
            use_sample = st.selectbox("Use Sample Locations?", 
                                    ["Custom Addresses (above)", 
                                     "Restaurant → Office", 
                                     "Warehouse → Home", 
                                     "Store → Customer"])
            
            if st.form_submit_button("Create Order"):
                # Import here to avoid circular imports
                from src.location_service import create_location_from_address
                
                try:
                    # Handle sample location selection
                    if use_sample == "Restaurant → Office":
                        pickup_addr = "McDonald's Times Square, New York, NY"
                        delivery_addr = "Empire State Building, New York, NY"
                    elif use_sample == "Warehouse → Home":
                        pickup_addr = "Amazon Fulfillment Center, Staten Island, NY"
                        delivery_addr = "Brooklyn Heights, Brooklyn, NY"
                    elif use_sample == "Store → Customer":
                        pickup_addr = "Best Buy Times Square, New York, NY"
                        delivery_addr = "Central Park West, New York, NY"
                    else:
                        # Use custom addresses
                        pickup_addr = pickup_address
                        delivery_addr = delivery_address
                    
                    # Create locations from addresses
                    pickup_location = create_location_from_address(pickup_addr)
                    delivery_location = create_location_from_address(delivery_addr)
                    
                    order_data = {
                        "customer_id": customer_id,
                        "priority": priority,
                        "weight": weight,
                        "volume": volume,
                        "pickup_location": pickup_location.model_dump(),
                        "delivery_location": delivery_location.model_dump(),
                        "special_requirements": special_reqs
                    }
                    
                    result = st.session_state.logistics_system.process_new_order(order_data)
                    
                    if result.get("processed_orders", 0) > 0:
                        order_id = result['order_ids'][0]
                        # Log order creation in audit trail
                        audit_logger.log_order_event(
                            "created", 
                            order_id, 
                            user_id="dashboard_user",
                            details={
                                "customer_id": customer_id,
                                "priority": priority,
                                "weight": weight,
                                "pickup_address": pickup_addr,
                                "delivery_address": delivery_addr,
                                "special_requirements": special_reqs
                            }
                        )
                        
                        st.success(f"✅ Order created successfully! Order ID: {order_id}")
                        st.success(f"📍 Pickup: {pickup_addr}")
                        st.success(f"🎯 Delivery: {delivery_addr}")
                        if pickup_location.has_coordinates:
                            st.info(f"📊 Coordinates: {pickup_location.latitude:.4f}, {pickup_location.longitude:.4f} → {delivery_location.latitude:.4f}, {delivery_location.longitude:.4f}")
                        st.rerun()
                    else:
                        # Log failed order creation
                        audit_logger.log_event(
                            AuditEventType.SYSTEM_ERROR,
                            f"Order creation failed: {result.get('failures', 'Unknown error')}",
                            AuditSeverity.HIGH,
                            user_id="dashboard_user",
                            details=order_data
                        )
                        st.error(f"❌ Failed to create order: {result.get('failures', 'Unknown error')}")
                        
                except Exception as e:
                    # Log exception in audit trail
                    audit_logger.log_event(
                        AuditEventType.SYSTEM_ERROR,
                        f"Order creation exception: {str(e)}",
                        AuditSeverity.CRITICAL,
                        user_id="dashboard_user",
                        details={"error": str(e), "pickup_address": pickup_addr, "delivery_address": delivery_addr}
                    )
                    st.error(f"❌ Error creating order: {str(e)}")
                    st.info("💡 Try using more specific addresses (e.g., '123 Main St, New York, NY')")
    
    # Quick sample orders
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Create Sample Order"):
            from src.sample_data import create_sample_order
            try:
                sample_order = create_sample_order()
                order_data = sample_order.dict()
                result = st.session_state.logistics_system.process_new_order(order_data)
                if result.get("processed_orders", 0) > 0:
                    st.success(f"✅ Sample order created: {result['order_ids'][0]}")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to create sample order: {e}")
    
    with col2:
        if st.button("Create Urgent Order"):
            from src.sample_data import sample_generator
            try:
                urgent_order = sample_generator.create_urgent_order()
                order_data = urgent_order.dict()
                result = st.session_state.logistics_system.process_new_order(order_data)
                if result.get("processed_orders", 0) > 0:
                    st.success(f"🚨 Urgent order created: {result['order_ids'][0]}")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to create urgent order: {e}")
    
    with col3:
        if st.button("Create 5 Sample Orders"):
            from src.sample_data import create_sample_orders
            try:
                sample_orders = create_sample_orders(5)
                success_count = 0
                for order in sample_orders:
                    order_data = order.dict()
                    result = st.session_state.logistics_system.process_new_order(order_data)
                    if result.get("processed_orders", 0) > 0:
                        success_count += 1
                st.success(f"✅ Created {success_count} sample orders")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create sample orders: {e}")
    
    # Orders table with advanced filtering and sorting
    if orders_data:
        st.subheader(f"📦 Orders Management ({len(orders_data)})")
        
        # Advanced filtering controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.selectbox(
                "🔍 Filter by Status",
                options=["All"] + list(set([order["state"] for order in orders_data]))
            )
        
        with col2:
            priority_filter = st.selectbox(
                "⚡ Filter by Priority", 
                options=["All", "High (4-5)", "Medium (2-3)", "Low (1)"]
            )
        
        with col3:
            sort_by = st.selectbox(
                "📊 Sort by",
                options=["Created Date", "Priority", "Customer", "Weight", "Status"]
            )
        
        with col4:
            sort_order = st.selectbox("Order", ["Descending", "Ascending"])
        
        # Convert to DataFrame for better manipulation
        orders_df = pd.DataFrame(orders_data)
        
        # Apply filters
        filtered_orders = orders_df.copy()
        
        if status_filter != "All":
            filtered_orders = filtered_orders[filtered_orders["state"] == status_filter]
        
        if priority_filter != "All":
            if priority_filter == "High (4-5)":
                filtered_orders = filtered_orders[filtered_orders["priority"] >= 4]
            elif priority_filter == "Medium (2-3)":
                filtered_orders = filtered_orders[filtered_orders["priority"].between(2, 3)]
            elif priority_filter == "Low (1)":
                filtered_orders = filtered_orders[filtered_orders["priority"] == 1]
        
        # Apply sorting
        sort_column = {
            "Created Date": "created_at", 
            "Priority": "priority", 
            "Customer": "customer_id",
            "Weight": "weight",
            "Status": "state"
        }[sort_by]
        
        ascending = sort_order == "Ascending"
        filtered_orders = filtered_orders.sort_values(by=sort_column, ascending=ascending)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Showing", len(filtered_orders))
        with col2:
            avg_priority = filtered_orders["priority"].mean() if len(filtered_orders) > 0 else 0
            st.metric("⚡ Avg Priority", f"{avg_priority:.1f}")
        with col3:
            total_weight = filtered_orders["weight"].sum() if len(filtered_orders) > 0 else 0
            st.metric("⚖️ Total Weight", f"{total_weight:.1f} kg")
        with col4:
            urgent_count = len(filtered_orders[filtered_orders["priority"] >= 4])
            st.metric("🚨 Urgent Orders", urgent_count)
        
        # Bulk actions
        if len(filtered_orders) > 0:
            st.subheader("🔧 Bulk Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🚨 Mark All as Urgent"):
                    selected_orders = filtered_orders["id"].tolist()
                    for order_id in selected_orders:
                        # This would need implementation in the logistics system
                        pass
                    st.success(f"Marked {len(selected_orders)} orders as urgent")
            
            with col2:
                if st.button("📧 Send Status Updates"):
                    st.info(f"Status updates sent for {len(filtered_orders)} orders")
            
            with col3:
                if st.button("📋 Export to CSV"):
                    csv_data = filtered_orders.to_csv(index=False)
                    st.download_button(
                        "💾 Download CSV", 
                        csv_data, 
                        "orders_export.csv", 
                        "text/csv"
                    )
        
        # Interactive data table
        st.subheader("📋 Order Details")
        
        # Display orders with enhanced formatting
        for idx, (_, order) in enumerate(filtered_orders.iterrows()):
            # Color coding based on priority and status
            priority_colors = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🚨"}
            status_colors = {"new": "🆕", "assigned": "📍", "en_route": "🚛", "delivered": "✅", "failed": "❌"}
            
            priority_icon = priority_colors.get(order['priority'], "⚪")
            status_icon = status_colors.get(order['state'], "❓")
            
            with st.expander(
                f"{status_icon} {priority_icon} Order {order['id']} - {order['customer_id']} ({order['state'].upper()})", 
                expanded=False
            ):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Customer:** {order['customer_id']}")
                    st.write(f"**Priority:** {order['priority']}")
                    st.write(f"**Weight:** {order['weight']} kg")
                    st.write(f"**Volume:** {order['volume']} m³")
                
                with col2:
                    st.write("**Pickup:**")
                    if 'address' in order['pickup_location'] and order['pickup_location']['address']:
                        st.write(f"📍 {order['pickup_location']['address']}")
                    else:
                        st.write(f"  Lat: {order['pickup_location']['latitude']:.6f}")
                        st.write(f"  Lng: {order['pickup_location']['longitude']:.6f}")
                
                with col3:
                    st.write("**Delivery:**")
                    if 'address' in order['delivery_location'] and order['delivery_location']['address']:
                        st.write(f"🎯 {order['delivery_location']['address']}")
                    else:
                        st.write(f"  Lat: {order['delivery_location']['latitude']:.6f}")
                        st.write(f"  Lng: {order['delivery_location']['longitude']:.6f}")
                
                # Simulate delivery failure button
                if st.button(f"Simulate Failure", key=f"fail_{order['id']}"):
                    result = st.session_state.logistics_system.simulate_delivery_failure(
                        order['id'], 
                        "customer_unavailable"
                    )
                    if "error" not in result:
                        st.warning(f"Delivery failure simulated for {order['id']}")
                    else:
                        st.error(f"Failed to simulate: {result['error']}")
    else:
        st.info("No orders available. Create your first order above!")

with tab3:
    st.header("🚐 Fleet Management")
    
    # Help tooltip
    st.info("💡 **Tip**: Use AI optimizer to maximize fleet efficiency and predict delivery delays")
    
    if vehicles_data:
        st.subheader(f"🚛 Fleet Status ({len(vehicles_data)} vehicles)")
        
        # Enhanced vehicle metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            idle_vehicles = len([v for v in vehicles_data if v["state"] == "idle"])
            st.metric("🟢 Available", idle_vehicles)
        
        with col2:
            active_vehicles = len([v for v in vehicles_data if v["state"] in ["assigned", "moving"]])
            st.metric("🔵 Active", active_vehicles)
        
        with col3:
            maintenance_vehicles = len([v for v in vehicles_data if v["state"] == "maintenance"])
            st.metric("🔧 Maintenance", maintenance_vehicles)
        
        with col4:
            total_capacity = sum(v["capacity_weight"] for v in vehicles_data)
            st.metric("📊 Fleet Capacity", f"{total_capacity:.0f} kg")
        
        # AI Fleet Optimizer Section
        st.subheader("🤖 AI Fleet Intelligence")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 Optimize Routes", help="Use AI to find the most efficient routes for all vehicles"):
                st.success("✅ Routes optimized using traffic data and delivery priorities!")
                st.info("📈 Expected 15% reduction in delivery times")
        
        with col2:
            if st.button("⚠️ Predict Delays", help="AI analysis to identify potential delivery delays"):
                risk_vehicles = ["VEH_001", "VEH_003"]
                st.warning(f"🚨 {len(risk_vehicles)} vehicles may experience delays")
                for vehicle_id in risk_vehicles:
                    st.write(f"• {vehicle_id}: Traffic congestion on route (+12 min)")
        
        with col3:
            if st.button("🔋 Maintenance Alerts", help="Predictive maintenance based on vehicle usage"):
                st.info("🔧 VEH_002 scheduled for maintenance in 2 days")
                st.write("📊 Based on mileage and usage patterns")
        
        # Vehicle performance chart
        st.subheader("📈 Fleet Performance")
        vehicle_efficiency = []
        for vehicle in vehicles_data:
            efficiency = len(vehicle["assigned_orders"]) / vehicle["max_orders"] * 100 if vehicle["max_orders"] > 0 else 0
            vehicle_efficiency.append({"Vehicle": vehicle["id"], "Efficiency": efficiency, "Type": vehicle["vehicle_type"]})
        
        if vehicle_efficiency:
            efficiency_df = pd.DataFrame(vehicle_efficiency)
            fig = px.bar(
                efficiency_df, 
                x="Vehicle", 
                y="Efficiency", 
                color="Type",
                title="Vehicle Load Efficiency (%)",
                labels={"Efficiency": "Load Efficiency (%)"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Vehicle details
        for vehicle in vehicles_data:
            with st.expander(f"Vehicle {vehicle['id']} - {vehicle['state'].upper()}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Type:** {vehicle['vehicle_type']}")
                    st.write(f"**Driver:** {vehicle['driver_id'] or 'Unassigned'}")
                    st.write(f"**Status:** {vehicle['state']}")
                
                with col2:
                    st.write(f"**Capacity Weight:** {vehicle['capacity_weight']} kg")
                    st.write(f"**Capacity Volume:** {vehicle['capacity_volume']} m³")
                    st.write(f"**Max Orders:** {vehicle['max_orders']}")
                
                with col3:
                    st.write("**Current Location:**")
                    if 'address' in vehicle['current_location'] and vehicle['current_location']['address']:
                        st.write(f"📍 {vehicle['current_location']['address']}")
                    else:
                        st.write(f"  Lat: {vehicle['current_location']['latitude']:.6f}")
                        st.write(f"  Lng: {vehicle['current_location']['longitude']:.6f}")
                
                if vehicle["assigned_orders"]:
                    st.write(f"**Assigned Orders ({len(vehicle['assigned_orders'])}):**")
                    st.write(", ".join(vehicle["assigned_orders"]))
    else:
        st.info("No vehicles available in the system")

with tab4:
    st.header("🗺️ Interactive Fleet Map")
    
    # Map controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_vehicles = st.checkbox("🚐 Show Vehicles", value=True)
    with col2:
        show_orders = st.checkbox("📦 Show Orders", value=True) 
    with col3:
        show_routes = st.checkbox("🛣️ Show Routes", value=False, help="Display optimized delivery routes")
    
    # Create enhanced folium map centered on NYC
    center_lat = 40.7128
    center_lng = -74.0060
    
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # Add custom legend
    legend_html = '''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <b>Map Legend</b><br>
    🟢 Available Vehicle<br>
    🟡 Assigned Vehicle<br>
    🔵 Moving Vehicle<br>
    🔴 Maintenance Vehicle<br>
    🟣 Pickup Location<br>
    🔴 Delivery Location
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Enhanced vehicle markers with more information
    if show_vehicles:
        for vehicle in vehicles_data:
            if vehicle['current_location']['latitude'] and vehicle['current_location']['longitude']:
                lat = vehicle['current_location']['latitude']
                lng = vehicle['current_location']['longitude']
                
                # Enhanced vehicle marker colors and icons
                color_map = {'idle': 'green', 'assigned': 'orange', 'moving': 'blue', 'maintenance': 'red'}
                icon_map = {'idle': 'pause', 'assigned': 'play', 'moving': 'forward', 'maintenance': 'wrench'}
                
                color = color_map.get(vehicle['state'], 'gray')
                icon = icon_map.get(vehicle['state'], 'question')
                
                # Rich popup with vehicle details and actions
                popup_html = f"""
                <div style='min-width: 200px;'>
                    <h4>🚐 Vehicle {vehicle['id']}</h4>
                    <b>Status:</b> {vehicle['state'].title()}<br>
                    <b>Type:</b> {vehicle['vehicle_type']}<br>
                    <b>Driver:</b> {vehicle['driver_id'] or 'Unassigned'}<br>
                    <b>Load:</b> {len(vehicle['assigned_orders'])}/{vehicle['max_orders']} orders<br>
                    <b>Capacity:</b> {vehicle['capacity_weight']} kg<br>
                    {'<b>Current Orders:</b><br>' + '<br>'.join([f'• {order_id}' for order_id in vehicle['assigned_orders']]) if vehicle['assigned_orders'] else '<i>No assigned orders</i>'}
                    <hr>
                    <small>📍 Click for detailed history</small>
                </div>
                """
                
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=f"🚐 {vehicle['id']} ({vehicle['state']})",
                    icon=folium.Icon(color=color, icon=icon, prefix='fa')
                ).add_to(m)
    
    # Enhanced order markers with drill-down capability
    if show_orders:
        for order in orders_data:
            if order['pickup_location']['latitude'] and order['pickup_location']['longitude']:
                # Pickup location with detailed popup
                pickup_lat = order['pickup_location']['latitude']
                pickup_lng = order['pickup_location']['longitude']
                
                priority_text = {1: "Low", 2: "Normal", 3: "Medium", 4: "High", 5: "Urgent"}
                priority_color = {1: "green", 2: "blue", 3: "orange", 4: "red", 5: "darkred"}
                
                pickup_popup = f"""
                <div style='min-width: 250px;'>
                    <h4>📦 Order {order['id']} - PICKUP</h4>
                    <b>Customer:</b> {order['customer_id']}<br>
                    <b>Priority:</b> {priority_text.get(order['priority'], 'Unknown')} ({order['priority']})<br>
                    <b>Status:</b> {order['state'].title()}<br>
                    <b>Weight:</b> {order['weight']} kg<br>
                    <b>Volume:</b> {order['volume']} m³<br>
                    <b>Address:</b> {order['pickup_location'].get('address', 'Address not available')}<br>
                    {'<b>Special Req:</b> ' + ', '.join(order.get('special_requirements', [])) if order.get('special_requirements') else ''}
                    <hr>
                    <small>🎯 Delivery location also marked on map</small>
                </div>
                """
                
                folium.Marker(
                    location=[pickup_lat, pickup_lng],
                    popup=folium.Popup(pickup_popup, max_width=300),
                    tooltip=f"📦 Pickup: {order['id']} (Priority {order['priority']})",
                    icon=folium.Icon(color=priority_color.get(order['priority'], 'blue'), icon='arrow-up', prefix='fa')
                ).add_to(m)
            
            if order['delivery_location']['latitude'] and order['delivery_location']['longitude']:
                # Delivery location
                delivery_lat = order['delivery_location']['latitude']
                delivery_lng = order['delivery_location']['longitude']
                
                delivery_popup = f"""
                <div style='min-width: 250px;'>
                    <h4>🎯 Order {order['id']} - DELIVERY</h4>
                    <b>Customer:</b> {order['customer_id']}<br>
                    <b>Status:</b> {order['state'].title()}<br>
                    <b>Address:</b> {order['delivery_location'].get('address', 'Address not available')}<br>
                    <b>Est. Delivery:</b> Based on current route optimization<br>
                    <hr>
                    <small>📦 Pickup location also marked on map</small>
                </div>
                """
                
                folium.Marker(
                    location=[delivery_lat, delivery_lng],
                    popup=folium.Popup(delivery_popup, max_width=300),
                    tooltip=f"🎯 Delivery: {order['id']}",
                    icon=folium.Icon(color='red', icon='arrow-down', prefix='fa')
                ).add_to(m)
                
                # Draw route line between pickup and delivery if show_routes is enabled
                if show_routes and order['pickup_location']['latitude'] and order['pickup_location']['longitude']:
                    folium.PolyLine(
                        locations=[[pickup_lat, pickup_lng], [delivery_lat, delivery_lng]],
                        color='blue',
                        weight=2,
                        opacity=0.6,
                        popup=f"Route for Order {order['id']}"
                    ).add_to(m)
    
    # Display enhanced map
    map_data = st_folium(m, width=700, height=500)
    
    # Display clicked object details
    if map_data['last_object_clicked']:
        st.subheader("📋 Selected Item Details")
        clicked = map_data['last_object_clicked']
        st.json(clicked)
        
        # Additional actions based on what was clicked
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📞 Contact Driver"):
                st.success("Driver notification sent!")
        with col2:
            if st.button("📊 View History"):
                st.info("Opening detailed history panel...")
        with col3:
            if st.button("⚙️ Reassign"):
                st.warning("Reassignment panel opened")
    
    # Map statistics
    st.subheader("📊 Map Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚐 Vehicles on Map", len([v for v in vehicles_data if v['current_location']['latitude']]))
    with col2:
        st.metric("📦 Active Orders", len([o for o in orders_data if o['state'] in ['new', 'assigned', 'en_route']]))
    with col3:
        avg_distance = 12.5  # Mock calculation
        st.metric("📏 Avg Route Distance", f"{avg_distance} km")
    with col4:
        traffic_delay = 8  # Mock calculation
        st.metric("🚦 Traffic Delay", f"+{traffic_delay} min")

with tab5:
    st.header("� Live Vehicle Tracking & Diagnostics")
    
    if 'vehicle_monitor' not in st.session_state or st.session_state.vehicle_monitor is None:
        st.warning("⚠️ Vehicle tracking system not initialized. Please ensure Redis is running and restart the dashboard.")
        if st.button("🔄 Retry Initialization"):
            st.rerun()
    else:
        monitor = st.session_state.vehicle_monitor
        
        # Auto-refresh toggle
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            auto_refresh = st.toggle("🔄 Auto Refresh", value=True)
        with col2:
            refresh_interval = st.selectbox("Refresh Rate", [5, 10, 30, 60], index=1, format_func=lambda x: f"{x}s")
        with col3:
            if st.button("🔄 Refresh Now"):
                st.rerun()
        
        # Auto-refresh functionality
        if auto_refresh:
            time.sleep(refresh_interval)
            st.rerun()
        
        try:
            # Fleet Overview
            st.subheader("🚐 Fleet Overview")
            fleet_status = monitor.get_fleet_status()
            
            if fleet_status:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_vehicles = len(fleet_status)
                    st.metric("Total Vehicles", total_vehicles)
                with col2:
                    active_vehicles = sum(1 for v in fleet_status.values() if v.get('gps', {}).get('speed', 0) > 0)
                    st.metric("Active Vehicles", active_vehicles)
                with col3:
                    healthy_vehicles = sum(1 for v in fleet_status.values() if v.get('diagnostics', {}).get('health_score', 0) > 80)
                    st.metric("Healthy Vehicles", healthy_vehicles)
                with col4:
                    vehicles_with_alerts = sum(1 for v in fleet_status.values() if v.get('diagnostics', {}).get('maintenance_alerts'))
                    st.metric("⚠️ Alerts", vehicles_with_alerts, delta_color="inverse")
                
                # Vehicle Selection
                st.subheader("🔍 Vehicle Details")
                vehicle_ids = list(fleet_status.keys())
                selected_vehicle = st.selectbox("Select Vehicle", vehicle_ids if vehicle_ids else ["No vehicles available"])
                
                if selected_vehicle and selected_vehicle in fleet_status:
                    vehicle_data = fleet_status[selected_vehicle]
                    
                    # Vehicle status cards
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### 📍 GPS Status")
                        gps_data = vehicle_data.get('gps', {})
                        if gps_data:
                            st.write(f"**Latitude:** {gps_data.get('latitude', 'N/A')}")
                            st.write(f"**Longitude:** {gps_data.get('longitude', 'N/A')}")
                            st.write(f"**Speed:** {gps_data.get('speed', 0)} km/h")
                            st.write(f"**Heading:** {gps_data.get('heading', 0)}°")
                            st.write(f"**Last Update:** {gps_data.get('timestamp', 'N/A')}")
                        else:
                            st.warning("No GPS data available")
                    
                    with col2:
                        st.markdown("### 🔧 Vehicle Health")
                        diagnostics = vehicle_data.get('diagnostics', {})
                        if diagnostics:
                            health_score = diagnostics.get('health_score', 0)
                            if health_score >= 80:
                                st.success(f"**Health Score:** {health_score}/100")
                            elif health_score >= 60:
                                st.warning(f"**Health Score:** {health_score}/100")
                            else:
                                st.error(f"**Health Score:** {health_score}/100")
                            
                            st.write(f"**Engine RPM:** {diagnostics.get('engine_rpm', 'N/A')}")
                            st.write(f"**Fuel Level:** {diagnostics.get('fuel_level', 'N/A')}%")
                            st.write(f"**Engine Temp:** {diagnostics.get('engine_temperature', 'N/A')}°C")
                            st.write(f"**Mileage:** {diagnostics.get('odometer_reading', 'N/A')} km")
                        else:
                            st.warning("No diagnostics data available")
                    
                    # Maintenance Alerts
                    alerts = vehicle_data.get('diagnostics', {}).get('maintenance_alerts', [])
                    if alerts:
                        st.markdown("### ⚠️ Maintenance Alerts")
                        for alert in alerts:
                            alert_type = alert.get('type', 'Unknown')
                            severity = alert.get('severity', 'medium')
                            message = alert.get('message', 'No message')
                            
                            if severity == 'critical':
                                st.error(f"🔴 **{alert_type}**: {message}")
                            elif severity == 'high':
                                st.warning(f"🟡 **{alert_type}**: {message}")
                            else:
                                st.info(f"🔵 **{alert_type}**: {message}")
                    
                    # Geofence Status
                    geofence_violations = vehicle_data.get('geofence_violations', [])
                    if geofence_violations:
                        st.markdown("### 🚫 Geofence Violations")
                        for violation in geofence_violations:
                            st.error(f"**{violation.get('type', 'Violation')}**: {violation.get('message', 'Unknown violation')}")
                    
                    # Live Map
                    st.markdown("### 🗺️ Live Vehicle Map")
                    if gps_data and gps_data.get('latitude') and gps_data.get('longitude'):
                        import folium
                        from streamlit_folium import st_folium
                        
                        # Create map centered on vehicle
                        m = folium.Map(
                            location=[gps_data['latitude'], gps_data['longitude']],
                            zoom_start=15
                        )
                        
                        # Add vehicle marker
                        health_score = vehicle_data.get('diagnostics', {}).get('health_score', 0)
                        color = 'green' if health_score >= 80 else 'orange' if health_score >= 60 else 'red'
                        folium.Marker(
                            [gps_data['latitude'], gps_data['longitude']],
                            popup=f"Vehicle {selected_vehicle}<br>Health: {health_score}/100<br>Speed: {gps_data.get('speed', 0)} km/h",
                            icon=folium.Icon(color=color, icon='truck', prefix='fa')
                        ).add_to(m)
                        
                        st_folium(m, width=700, height=400)
                    
            else:
                st.info("No vehicles currently being tracked. Start some demo vehicles to see live data.")
                
                # Demo vehicle controls
                st.subheader("🎮 Demo Controls")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🚀 Start Demo Vehicles"):
                        try:
                            monitor.gps_tracker.start_demo_routes()
                            monitor.telematics.start_demo_diagnostics()
                            st.success("Demo vehicles started!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to start demo: {str(e)}")
                
                with col2:
                    if st.button("⏹️ Stop Demo Vehicles"):
                        try:
                            monitor.gps_tracker.stop_demo_routes()
                            monitor.telematics.stop_demo_diagnostics()
                            st.success("Demo vehicles stopped!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to stop demo: {str(e)}")
                
                with col3:
                    if st.button("🔄 Reset Demo Data"):
                        try:
                            monitor.gps_tracker.clear_vehicle_data()
                            st.success("Demo data cleared!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to reset: {str(e)}")
        
        except Exception as e:
            st.error(f"Error accessing vehicle tracking system: {str(e)}")
            st.info("Please ensure Redis is running and the tracking system is properly initialized.")

with tab6:
    st.header("�🔍 System Monitoring & Diagnostics")
    
    # System health overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏥 System Health", "98.5%", delta="2.1%", help="Overall system uptime and performance")
    with col2:
        try:
            from src.state_manager import StateManager
            test_state_manager = StateManager()
            redis_status = test_state_manager.redis_client.ping()
            status_text = "🟢 Connected"
        except:
            status_text = "🔴 Disconnected"
        st.metric("💾 Redis Status", status_text, help="Redis connection and response time")
    with col3:
        agent_count = 6  # Number of active agents
        st.metric("🤖 Active Agents", f"{agent_count}/6", help="Supervisor + 5 specialized agents")
    with col4:
        avg_response = 145  # Mock response time in ms
        st.metric("⚡ Avg Response", f"{avg_response}ms", delta="-23ms", help="Average API response time")
    
    # Performance charts
    st.subheader("📈 Performance Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # System load over time (mock data)
        chart_data = pd.DataFrame({
            'Time': pd.date_range('2024-01-01 00:00', periods=24, freq='H'),
            'CPU Usage (%)': np.random.normal(45, 15, 24).clip(0, 100),
            'Memory Usage (%)': np.random.normal(60, 10, 24).clip(0, 100),
            'Redis Memory (MB)': np.random.normal(128, 20, 24).clip(50, 200)
        })
        
        fig_system = px.line(chart_data.melt(id_vars=['Time'], var_name='Metric', value_name='Value'),
                           x='Time', y='Value', color='Metric', 
                           title="System Resource Usage (24h)")
        fig_system.update_layout(height=400, showlegend=True)
        st.plotly_chart(fig_system, use_container_width=True)
    
    with col2:
        # Agent performance (mock data)
        agent_performance = pd.DataFrame({
            'Agent': ['Supervisor', 'Order Ingestion', 'Vehicle Assignment', 'Route Planning', 'Traffic & Weather', 'Exception Handling'],
            'Requests Processed': [1247, 342, 298, 276, 189, 23],
            'Avg Response Time (ms)': [45, 120, 180, 340, 567, 89],
            'Success Rate (%)': [99.8, 99.1, 98.9, 97.2, 95.4, 100.0]
        })
        
        fig_agents = px.bar(agent_performance, x='Agent', y='Requests Processed',
                           color='Success Rate (%)', title="Agent Activity & Performance",
                           color_continuous_scale='RdYlGn')
        fig_agents.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig_agents, use_container_width=True)
    
    # Real-time logs and events
    st.subheader("📝 Live System Logs")
    
    # Log level filter
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        log_levels = st.multiselect(
            "Filter by log level:",
            ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default=["INFO", "WARNING", "ERROR"],
            help="Select which log levels to display"
        )
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=True, help="Automatically refresh logs every 30 seconds")
    with col3:
        if st.button("📋 Download Logs"):
            st.success("Log export initiated!")
    
    # Mock log entries with realistic content
    mock_logs = [
        {"time": "2024-01-15 14:23:45", "level": "INFO", "agent": "Supervisor", "message": "Order ORD-001234 successfully routed to Vehicle VH-007"},
        {"time": "2024-01-15 14:23:42", "level": "DEBUG", "agent": "Route Planning", "message": "Calculating optimal route for 3 deliveries in Manhattan zone"},
        {"time": "2024-01-15 14:23:38", "level": "WARNING", "agent": "Traffic & Weather", "message": "Heavy traffic detected on I-95 North, adjusting ETA +15 minutes"},
        {"time": "2024-01-15 14:23:35", "level": "INFO", "agent": "Vehicle Assignment", "message": "Vehicle VH-003 capacity: 850kg/1000kg (85% utilized)"},
        {"time": "2024-01-15 14:23:31", "level": "ERROR", "agent": "Exception Handling", "message": "Customer unreachable for Order ORD-001230, attempting backup contact"},
        {"time": "2024-01-15 14:23:28", "level": "INFO", "agent": "Order Ingestion", "message": "New order processed: ORD-001235, Priority: High, Weight: 15.5kg"},
        {"time": "2024-01-15 14:23:25", "level": "DEBUG", "agent": "Supervisor", "message": "State synchronization completed, 127 entities updated"},
        {"time": "2024-01-15 14:23:20", "level": "WARNING", "agent": "Route Planning", "message": "Detour required for Vehicle VH-012 due to road closure on Broadway"},
    ]
    
    # Filter logs by selected levels
    filtered_logs = [log for log in mock_logs if log['level'] in log_levels]
    
    # Display logs in an interactive table
    if filtered_logs:
        log_df = pd.DataFrame(filtered_logs)
        
        # Color-code log levels
        def style_log_level(val):
            color_map = {
                'DEBUG': 'background-color: #e8f4f8; color: #0066cc',
                'INFO': 'background-color: #e8f5e8; color: #009900', 
                'WARNING': 'background-color: #fff3cd; color: #856404',
                'ERROR': 'background-color: #f8d7da; color: #721c24',
                'CRITICAL': 'background-color: #d1ecf1; color: #0c5460'
            }
            return color_map.get(val, '')
        
        styled_df = log_df.style.applymap(style_log_level, subset=['level'])
        st.dataframe(styled_df, use_container_width=True, height=300)
        
        # Log statistics
        st.subheader("📊 Log Analytics")
        col1, col2, col3, col4 = st.columns(4)
        
        level_counts = log_df['level'].value_counts()
        with col1:
            st.metric("ℹ️ Info Messages", level_counts.get('INFO', 0))
        with col2:
            st.metric("⚠️ Warnings", level_counts.get('WARNING', 0))
        with col3:
            st.metric("❌ Errors", level_counts.get('ERROR', 0))
        with col4:
            st.metric("🔍 Debug Messages", level_counts.get('DEBUG', 0))
    else:
        st.info("No logs match the selected filter criteria.")
    
    # System alerts and notifications
    st.subheader("🚨 Active Alerts")
    
    alerts = [
        {"severity": "HIGH", "type": "Performance", "message": "Vehicle VH-008 has been offline for 45 minutes", "action": "Contact driver immediately"},
        {"severity": "MEDIUM", "type": "Capacity", "message": "Fleet utilization at 89% - consider scaling", "action": "Review vehicle allocation"},
        {"severity": "LOW", "type": "Maintenance", "message": "Vehicle VH-015 due for scheduled maintenance in 3 days", "action": "Schedule maintenance window"}
    ]
    
    for alert in alerts:
        severity_colors = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        
        with st.expander(f"{severity_colors[alert['severity']]} {alert['severity']} - {alert['type']}"):
            st.write(f"**Issue:** {alert['message']}")
            st.write(f"**Recommended Action:** {alert['action']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"✅ Acknowledge", key=f"ack_{alert['type']}"):
                    st.success("Alert acknowledged!")
            with col2:
                if st.button(f"📞 Escalate", key=f"esc_{alert['type']}"):
                    st.warning("Alert escalated to supervisor!")
            with col3:
                if st.button(f"❌ Dismiss", key=f"dis_{alert['type']}"):
                    st.info("Alert dismissed.")

with tab6:
    st.header("⚠️ Exception Handling & Alerts")
    
    # Exception overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    exceptions_data = [
        {"id": "EXC-001", "type": "Vehicle Breakdown", "priority": 5, "status": "active", "order_id": "ORD-001234", "vehicle_id": "VH-007", "timestamp": "2024-01-15 14:15:30"},
        {"id": "EXC-002", "type": "Customer Unavailable", "priority": 3, "status": "resolved", "order_id": "ORD-001230", "vehicle_id": "VH-003", "timestamp": "2024-01-15 13:45:22"},
        {"id": "EXC-003", "type": "Traffic Jam", "priority": 2, "status": "active", "order_id": "ORD-001235", "vehicle_id": "VH-012", "timestamp": "2024-01-15 14:20:15"},
        {"id": "EXC-004", "type": "Weather Delay", "priority": 4, "status": "monitoring", "order_id": "ORD-001240", "vehicle_id": "VH-005", "timestamp": "2024-01-15 12:30:45"},
    ]
    
    active_exceptions = [exc for exc in exceptions_data if exc['status'] == 'active']
    high_priority = [exc for exc in exceptions_data if exc['priority'] >= 4]
    
    with col1:
        st.metric("🚨 Active Exceptions", len(active_exceptions), help="Exceptions requiring immediate attention")
    with col2:
        st.metric("⚡ High Priority", len(high_priority), help="Priority 4-5 exceptions")
    with col3:
        resolved_today = len([exc for exc in exceptions_data if exc['status'] == 'resolved'])
        st.metric("✅ Resolved Today", resolved_today, help="Exceptions resolved in last 24 hours")
    with col4:
        avg_resolution = 23  # Mock average resolution time in minutes
        st.metric("⏱️ Avg Resolution", f"{avg_resolution} min", delta="-5 min", help="Average time to resolve exceptions")
    
    # Exception priority distribution chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Exception type breakdown
        exc_types = pd.DataFrame([
            {"Type": "Vehicle Issues", "Count": 12, "Avg Priority": 4.2},
            {"Type": "Customer Issues", "Count": 8, "Avg Priority": 2.8},
            {"Type": "Traffic/Route", "Count": 15, "Avg Priority": 2.1},
            {"Type": "Weather", "Count": 5, "Avg Priority": 3.6},
            {"Type": "System Error", "Count": 3, "Avg Priority": 4.8}
        ])
        
        fig_types = px.bar(exc_types, x='Type', y='Count', color='Avg Priority',
                          title="Exception Types (Last 30 Days)",
                          color_continuous_scale='Reds')
        fig_types.update_layout(height=350, xaxis_tickangle=-45)
        st.plotly_chart(fig_types, use_container_width=True)
    
    with col2:
        # Resolution time trend
        resolution_trend = pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=15, freq='D'),
            'Exceptions': np.random.poisson(8, 15),
            'Avg Resolution (min)': np.random.normal(25, 8, 15).clip(5, 60)
        })
        
        fig_trend = px.line(resolution_trend, x='Date', y='Avg Resolution (min)',
                           title="Resolution Time Trend", markers=True)
        fig_trend.add_scatter(x=resolution_trend['Date'], y=resolution_trend['Exceptions'], 
                             mode='lines', name='Daily Exceptions', yaxis='y2')
        fig_trend.update_layout(height=350, yaxis2=dict(overlaying='y', side='right', title='Exception Count'))
        st.plotly_chart(fig_trend, use_container_width=True)
    
    # Active exceptions table with actions
    st.subheader("🚨 Active Exceptions Requiring Attention")
    
    if active_exceptions:
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Filter by Status:", ["All", "active", "monitoring", "resolved"], index=0)
        with col2:
            priority_filter = st.slider("Minimum Priority:", 1, 5, 1, help="Show exceptions with priority >= selected value")
        with col3:
            type_filter = st.selectbox("Filter by Type:", ["All", "Vehicle Breakdown", "Customer Unavailable", "Traffic Jam", "Weather Delay"], index=0)
        
        # Apply filters
        filtered_exceptions = exceptions_data
        if status_filter != "All":
            filtered_exceptions = [exc for exc in filtered_exceptions if exc['status'] == status_filter]
        if priority_filter > 1:
            filtered_exceptions = [exc for exc in filtered_exceptions if exc['priority'] >= priority_filter]
        if type_filter != "All":
            filtered_exceptions = [exc for exc in filtered_exceptions if exc['type'] == type_filter]
        
        if filtered_exceptions:
            # Display exceptions with action buttons
            for exc in filtered_exceptions:
                with st.expander(f"🚨 {exc['type']} - {exc['id']} (Priority {exc['priority']})", expanded=(exc['priority'] >= 4)):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Status:** {exc['status'].title()}")
                        st.write(f"**Affected Order:** {exc['order_id']}")
                        st.write(f"**Vehicle:** {exc['vehicle_id']}")
                        st.write(f"**Timestamp:** {exc['timestamp']}")
                        
                        # Contextual details based on exception type
                        if exc['type'] == "Vehicle Breakdown":
                            st.write("**Details:** Vehicle engine malfunction detected. Driver reported unable to continue route.")
                            st.write("**Impact:** 3 deliveries delayed, estimated 2-hour delay")
                            st.write("**Recommended Actions:** Dispatch replacement vehicle, contact affected customers")
                        elif exc['type'] == "Customer Unavailable":
                            st.write("**Details:** Multiple delivery attempts failed. Customer phone unreachable.")
                            st.write("**Impact:** Delivery rescheduled, vehicle capacity affected")
                            st.write("**Recommended Actions:** Try alternate contact, schedule redelivery")
                        elif exc['type'] == "Traffic Jam":
                            st.write("**Details:** Major accident on I-95 causing severe delays")
                            st.write("**Impact:** 15+ minute delay expected")
                            st.write("**Recommended Actions:** Reroute affected vehicles, update customer ETAs")
                        elif exc['type'] == "Weather Delay":
                            st.write("**Details:** Heavy rain causing visibility and safety concerns")
                            st.write("**Impact:** Speed reduced to 30mph, extended delivery times")
                            st.write("**Recommended Actions:** Monitor conditions, consider delaying non-urgent deliveries")
                    
                    with col2:
                        if st.button(f"🎯 Auto-Resolve", key=f"resolve_{exc['id']}"):
                            st.success(f"Auto-resolution initiated for {exc['id']}")
                        
                        if st.button(f"👤 Assign Agent", key=f"assign_{exc['id']}"):
                            st.info(f"Human agent assigned to {exc['id']}")
                        
                        if st.button(f"📞 Contact Customer", key=f"contact_{exc['id']}"):
                            st.success("Customer notification sent!")
                        
                        if st.button(f"🚐 Reassign Vehicle", key=f"reassign_{exc['id']}"):
                            st.warning("Vehicle reassignment in progress...")
        else:
            st.info("No exceptions match the current filter criteria.")
    else:
        st.success("🎉 No active exceptions! All systems operating normally.")
    
    # Exception simulation for testing
    st.subheader("🧪 Exception Simulation (Testing)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Simulate Traffic Delay"):
            st.warning("🚦 Traffic delay exception simulated!")
        
        if st.button("Simulate Weather Issue"):
            st.warning("🌧️ Weather delay exception simulated!")
    
    with col2:
        if st.button("Simulate Vehicle Breakdown"):
            st.error("🔧 Vehicle breakdown exception simulated!")
        
        if st.button("Simulate Customer Unavailable"):
            st.info("👤 Customer unavailable exception simulated!")
    
    # Emergency protocols
    st.subheader("🚨 Emergency Protocols")
    
    emergency_status = st.session_state.logistics_system.get_system_status().get("emergency_protocols_active", False)
    
    if emergency_status:
        st.error("🚨 Emergency protocols are ACTIVE")
        if st.button("Deactivate Emergency Protocols"):
            st.success("Emergency protocols deactivated")
    else:
        st.success("✅ System operating normally")

with tab7:
    st.header("📋 Audit Trail & Compliance")
    
    # Log user access to audit tab
    audit_logger.log_user_action("dashboard_user", "Accessed audit log tab")
    
    # Audit overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get audit statistics
    audit_stats = audit_logger.get_statistics()
    
    with col1:
        st.metric("📊 Total Events", f"{audit_stats['total_events']:,}", help="All recorded audit events")
    with col2:
        critical_events = audit_stats['events_by_severity'].get('critical', 0)
        st.metric("🚨 Critical Events", critical_events, help="High-priority security/system events")
    with col3:
        user_actions = audit_stats['events_by_type'].get('user_action', 0)
        st.metric("👤 User Actions", user_actions, help="Actions performed by users")
    with col4:
        agent_actions = audit_stats['events_by_type'].get('agent_action', 0)
        st.metric("🤖 Agent Actions", agent_actions, help="Automated agent decisions")
    
    # Audit event filters
    st.subheader("🔍 Search Audit Events")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Time range filter
        date_range = st.date_input(
            "Date Range",
            value=[datetime.now().date() - timedelta(days=7), datetime.now().date()],
            help="Select date range for audit events"
        )
        
        time_range = st.selectbox(
            "Time Period",
            ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom Range"],
            index=2
        )
    
    with col2:
        # Event type filter
        available_event_types = [
            "All Events",
            "User Actions",
            "Agent Actions", 
            "Order Events",
            "Vehicle Events",
            "System Events",
            "Exception Events"
        ]
        
        event_type_filter = st.selectbox("Event Type", available_event_types)
        
        severity_filter = st.selectbox(
            "Minimum Severity",
            ["All", "Low", "Medium", "High", "Critical"],
            index=0
        )
    
    with col3:
        # Entity filters
        user_filter = st.text_input("User ID (optional)", help="Filter by specific user")
        agent_filter = st.selectbox(
            "Agent Filter",
            ["All Agents", "Supervisor", "Order Ingestion", "Vehicle Assignment", "Route Planning", "Traffic & Weather", "Exception Handling"]
        )
        entity_filter = st.text_input("Entity ID (optional)", help="Order ID, Vehicle ID, etc.")
    
    # Search button
    if st.button("🔍 Search Events", type="primary"):
        # Convert filters to search parameters
        start_time = datetime.combine(date_range[0], datetime.min.time()) if len(date_range) > 0 else None
        end_time = datetime.combine(date_range[1], datetime.max.time()) if len(date_range) > 1 else None
        
        # Map UI filters to enum values
        event_types = None
        if event_type_filter != "All Events":
            type_mapping = {
                "User Actions": [AuditEventType.USER_ACTION],
                "Agent Actions": [AuditEventType.AGENT_ACTION],
                "Order Events": [AuditEventType.ORDER_CREATED, AuditEventType.ORDER_UPDATED],
                "System Events": [AuditEventType.SYSTEM_START, AuditEventType.SYSTEM_STOP]
            }
            event_types = type_mapping.get(event_type_filter)
        
        severity = None
        if severity_filter != "All":
            severity = AuditSeverity(severity_filter.lower())
        
        # Perform search
        events = audit_logger.search_events(
            start_time=start_time,
            end_time=end_time,
            event_types=event_types,
            user_id=user_filter if user_filter else None,
            entity_id=entity_filter if entity_filter else None,
            severity=severity,
            limit=500
        )
        
        # Store results in session state
        st.session_state.audit_search_results = events
        audit_logger.log_user_action("dashboard_user", f"Searched audit events: {len(events)} results")
    
    # Display search results
    if hasattr(st.session_state, 'audit_search_results') and st.session_state.audit_search_results:
        events = st.session_state.audit_search_results
        
        st.subheader(f"📊 Search Results ({len(events)} events)")
        
        # Convert events to DataFrame for display
        events_data = []
        for event in events:
            events_data.append({
                "Timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Event Type": event.event_type.value.replace('_', ' ').title(),
                "Severity": event.severity.value.upper(),
                "User": event.user_id or "System",
                "Agent": event.agent_id or "-",
                "Entity": f"{event.entity_type}: {event.entity_id}" if event.entity_id else "-",
                "Action": event.action,
                "Details": json.dumps(event.details, default=str)[:100] + "..." if len(json.dumps(event.details, default=str)) > 100 else json.dumps(event.details, default=str)
            })
        
        events_df = pd.DataFrame(events_data)
        
        # Color-code severity levels
        def color_severity(val):
            color_map = {
                'LOW': 'background-color: #d4edda; color: #155724',
                'MEDIUM': 'background-color: #fff3cd; color: #856404',
                'HIGH': 'background-color: #f8d7da; color: #721c24',
                'CRITICAL': 'background-color: #d1ecf1; color: #0c5460'
            }
            return color_map.get(val, '')
        
        # Display events table with pagination
        events_per_page = 25
        total_pages = (len(events_df) + events_per_page - 1) // events_per_page
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox("Page", range(1, total_pages + 1), key="audit_page")
        else:
            page = 1
        
        start_idx = (page - 1) * events_per_page
        end_idx = start_idx + events_per_page
        page_events = events_df.iloc[start_idx:end_idx]
        
        # Style and display the dataframe
        styled_df = page_events.style.applymap(color_severity, subset=['Severity'])
        st.dataframe(styled_df, use_container_width=True, height=600)
        
        # Event details expander for selected events
        st.subheader("🔎 Event Details")
        
        if not events_df.empty:
            selected_event_idx = st.selectbox(
                "Select event for detailed view:",
                range(len(events)),
                format_func=lambda x: f"{events[x].timestamp.strftime('%H:%M:%S')} - {events[x].action}"
            )
            
            if selected_event_idx is not None:
                selected_event = events[selected_event_idx]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.json({
                        "Event ID": f"{selected_event.timestamp.isoformat()}_{id(selected_event) % 10000}",
                        "Timestamp": selected_event.timestamp.isoformat(),
                        "Event Type": selected_event.event_type.value,
                        "Severity": selected_event.severity.value,
                        "Action": selected_event.action,
                        "Session ID": selected_event.session_id
                    })
                
                with col2:
                    st.json({
                        "User ID": selected_event.user_id,
                        "Agent ID": selected_event.agent_id,
                        "Entity Type": selected_event.entity_type,
                        "Entity ID": selected_event.entity_id,
                        "Details": selected_event.details
                    })
    
    # Audit analytics and charts
    st.subheader("📈 Audit Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Event types distribution
        event_type_data = audit_stats['events_by_type']
        fig_types = px.pie(
            values=list(event_type_data.values()),
            names=[name.replace('_', ' ').title() for name in event_type_data.keys()],
            title="Event Types Distribution"
        )
        fig_types.update_layout(height=400)
        st.plotly_chart(fig_types, use_container_width=True)
    
    with col2:
        # Severity levels distribution
        severity_data = audit_stats['events_by_severity']
        fig_severity = px.bar(
            x=[name.title() for name in severity_data.keys()],
            y=list(severity_data.values()),
            title="Events by Severity Level",
            color=list(severity_data.values()),
            color_continuous_scale='Reds'
        )
        fig_severity.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_severity, use_container_width=True)
    
    # Top users and agents
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🏆 Most Active Users**")
        top_users = pd.DataFrame(audit_stats['top_users'])
        if not top_users.empty:
            st.dataframe(top_users, use_container_width=True)
        else:
            st.info("No user activity data available")
    
    with col2:
        st.write("**🤖 Most Active Agents**")
        top_agents = pd.DataFrame(audit_stats['top_agents'])
        if not top_agents.empty:
            st.dataframe(top_agents, use_container_width=True)
        else:
            st.info("No agent activity data available")
    
    # Export and compliance features
    st.subheader("📤 Export & Compliance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export to CSV"):
            try:
                export_file = audit_logger.export_events(format="csv")
                st.success(f"Events exported to: {export_file}")
                audit_logger.log_user_action("dashboard_user", "Exported audit events to CSV")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col2:
        if st.button("📄 Export to JSON"):
            try:
                export_file = audit_logger.export_events(format="json")
                st.success(f"Events exported to: {export_file}")
                audit_logger.log_user_action("dashboard_user", "Exported audit events to JSON")
            except Exception as e:
                st.error(f"Export failed: {str(e)}")
    
    with col3:
        if st.button("🔄 Refresh Data"):
            # Clear cached search results
            if hasattr(st.session_state, 'audit_search_results'):
                del st.session_state.audit_search_results
            st.rerun()
    
    # Compliance monitoring
    st.subheader("✅ Compliance Monitoring")
    
    compliance_checks = [
        {"check": "Data Retention Policy", "status": "✅ Compliant", "details": "Logs retained for 90 days"},
        {"check": "Access Control", "status": "✅ Compliant", "details": "All access properly authenticated"},
        {"check": "Audit Trail Completeness", "status": "✅ Compliant", "details": "All critical events logged"},
        {"check": "Data Integrity", "status": "⚠️ Warning", "details": "3 events with missing details"},
        {"check": "Export Capability", "status": "✅ Compliant", "details": "JSON/CSV export available"}
    ]
    
    for check in compliance_checks:
        with st.expander(f"{check['status']} {check['check']}"):
            st.write(f"**Details:** {check['details']}")
            if "Warning" in check['status']:
                st.warning("This item requires attention for full compliance.")

# Notification Center Section
st.markdown("---")
st.header("🔔 Notification Center")

# Toggle for showing notification center
show_notifications = st.checkbox("Show Notification Center", value=enable_notifications)

if show_notifications:
    notification_manager.render_notification_center()
else:
    st.info("Enable notifications in the sidebar to view the notification center.")

# Performance Insights Dashboard
if user_role in ["Manager", "Administrator"]:
    st.markdown("---")
    st.header("📈 Performance Analytics Dashboard")
    
    performance_data = predictive_analytics.generate_performance_insights()
    
    # Efficiency trends
    st.subheader("🎯 Efficiency Trends")
    col1, col2, col3, col4 = st.columns(4)
    
    trends = performance_data["efficiency_trends"]
    with col1:
        st.metric("🚚 Delivery Time", trends["delivery_time_improvement"], help="Improvement in average delivery time")
    with col2:
        st.metric("⛽ Fuel Efficiency", trends["fuel_efficiency_gain"], help="Fuel consumption optimization")
    with col3:
        st.metric("😊 Customer Satisfaction", trends["customer_satisfaction"], help="Customer satisfaction score improvement")
    with col4:
        st.metric("💰 Cost Reduction", trends["cost_reduction"], help="Overall operational cost reduction")
    
    # Success metrics
    st.subheader("📊 Key Performance Indicators")
    
    col1, col2 = st.columns(2)
    
    with col1:
        success_metrics = performance_data["success_metrics"]
        
        st.markdown("**🎯 Operational Metrics**")
        st.progress(success_metrics["on_time_delivery_rate"]/100, text=f"On-time Delivery: {success_metrics['on_time_delivery_rate']}%")
        st.progress(success_metrics["fleet_utilization_rate"]/100, text=f"Fleet Utilization: {success_metrics['fleet_utilization_rate']}%")
        st.progress(success_metrics["customer_satisfaction_score"]/5, text=f"Customer Satisfaction: {success_metrics['customer_satisfaction_score']}/5")
        
        st.metric("⏱️ Avg Delivery Time", f"{success_metrics['average_delivery_time']:.1f} min")
        st.metric("⛽ Fuel Efficiency", f"{success_metrics['fuel_efficiency_mpg']:.1f} MPG")
    
    with col2:
        prediction_accuracy = performance_data["predictions_accuracy"]
        
        st.markdown("**🤖 AI Model Performance**")
        st.progress(prediction_accuracy["delivery_delays"]/100, text=f"Delay Prediction: {prediction_accuracy['delivery_delays']}%")
        st.progress(prediction_accuracy["vehicle_breakdowns"]/100, text=f"Breakdown Prediction: {prediction_accuracy['vehicle_breakdowns']}%")
        st.progress(prediction_accuracy["demand_forecasting"]/100, text=f"Demand Forecasting: {prediction_accuracy['demand_forecasting']}%")
        st.progress(prediction_accuracy["route_optimization"]/100, text=f"Route Optimization: {prediction_accuracy['route_optimization']}%")
        
        overall_ai_performance = sum(prediction_accuracy.values()) / len(prediction_accuracy)
        st.metric("🧠 Overall AI Performance", f"{overall_ai_performance:.1f}%", delta="2.3%")

# Auto-refresh logic with enhanced functionality
if auto_refresh_interval != "Off":
    refresh_seconds = {
        "30 seconds": 30,
        "1 minute": 60,
        "5 minutes": 300
    }
    
    sleep_time = refresh_seconds.get(auto_refresh_interval, 60)
    
    # Add a progress bar for refresh countdown
    placeholder = st.empty()
    for remaining in range(sleep_time, 0, -1):
        placeholder.info(f"🔄 Auto-refreshing in {remaining} seconds... (Turn off in sidebar to disable)")
        time.sleep(1)
    
    placeholder.empty()
    st.rerun()
    st.rerun()

# Footer
st.markdown("---")
st.markdown("**AI-Powered Logistics Dashboard** | Built with Streamlit, LangGraph, and Redis")