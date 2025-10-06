"""
Enhanced Package Tracking Dashboard Integration

This module integrates the QR/Barcode scanning and BLE/NFC functionality
into the Streamlit dashboard for comprehensive package tracking.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

try:
    from src.tracking.package_tracker import PackageTrackingSystem, PackageStatus, ScanType
    from src.tracking.barcode_scanner import BarcodeScanner, BarcodeFormat
    from src.tracking.ble_nfc_integration import BLENFCIntegrationSystem, BLEBeaconType, NFCTagType
except ImportError:
    # Handle import for development
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from package_tracker import PackageTrackingSystem, PackageStatus, ScanType
    from barcode_scanner import BarcodeScanner, BarcodeFormat
    from ble_nfc_integration import BLENFCIntegrationSystem, BLEBeaconType, NFCTagType


def render_package_tracking_tab():
    """Render the Package Tracking tab in the dashboard"""
    st.header("📦 Package Tracking & Scanning")
    
    # Initialize tracking system in session state
    if 'package_tracker' not in st.session_state:
        st.session_state.package_tracker = PackageTrackingSystem()
    
    tracker = st.session_state.package_tracker
    
    # Create tabs for different tracking features
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📱 QR/Barcode Scanning", 
        "📡 BLE/NFC Tracking", 
        "📊 Package Journey", 
        "🎯 Batch Operations",
        "📈 Analytics"
    ])
    
    with tab1:
        render_qr_barcode_section(tracker)
    
    with tab2:
        render_ble_nfc_section(tracker)
    
    with tab3:
        render_package_journey_section(tracker)
    
    with tab4:
        render_batch_operations_section(tracker)
    
    with tab5:
        render_tracking_analytics(tracker)


def render_qr_barcode_section(tracker):
    """Render QR Code and Barcode scanning section"""
    st.subheader("🏷️ QR Code & Barcode Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Generate Codes")
        
        # Package ID input
        package_id = st.text_input("Package ID", value="PKG_DEMO_001", key="qr_package_id")
        order_id = st.text_input("Order ID", value="ORD_001", key="qr_order_id")
        
        # Code generation options
        st.write("**Generation Options:**")
        generate_qr = st.checkbox("Generate QR Code", value=True)
        generate_barcode = st.checkbox("Generate Barcode", value=True)
        
        if generate_barcode:
            barcode_format = st.selectbox(
                "Barcode Format",
                ["code128", "code39", "ean13"],
                key="barcode_format"
            )
        
        if st.button("🏷️ Generate Package Codes"):
            if package_id and order_id:
                # Create package tracking with codes
                tracking_options = {
                    "enable_qr": generate_qr,
                    "enable_barcode": generate_barcode
                }
                
                try:
                    journey = tracker.create_package_tracking(
                        package_id, order_id, tracking_options
                    )
                    
                    st.success(f"✅ Generated tracking codes for {package_id}")
                    
                    # Display generated codes
                    for tag in journey.tags:
                        if tag.tag_type.value == "qr_code":
                            st.code(f"QR Code: {tag.data['qr_code'][:50]}...", language="text")
                        elif tag.tag_type.value in ["code128", "barcode_128"]:
                            st.code(f"Barcode: {tag.data['barcode']}", language="text")
                    
                except Exception as e:
                    st.error(f"❌ Error generating codes: {e}")
            else:
                st.warning("Please enter both Package ID and Order ID")
    
    with col2:
        st.write("### Scan Codes")
        
        scan_method = st.radio(
            "Scan Method",
            ["QR Code", "Barcode", "Simulate Scan"],
            key="scan_method"
        )
        
        if scan_method == "QR Code":
            qr_data = st.text_area("QR Code Data", height=100, key="qr_scan_input")
            
            if st.button("📱 Scan QR Code"):
                if qr_data:
                    result = tracker.qr_scanner.scan_qr_code(qr_data)
                    display_scan_result(result)
                else:
                    st.warning("Please enter QR code data")
        
        elif scan_method == "Barcode":
            barcode_data = st.text_input("Barcode Data", key="barcode_scan_input")
            
            if st.button("🏷️ Scan Barcode"):
                if barcode_data:
                    result = tracker.qr_scanner.scan_barcode(barcode_data)
                    display_scan_result(result)
                else:
                    st.warning("Please enter barcode data")
        
        elif scan_method == "Simulate Scan":
            sim_package_id = st.selectbox(
                "Select Package to Scan",
                list(tracker.packages.keys()) if tracker.packages else ["No packages available"],
                key="sim_package_select"
            )
            
            sim_scan_type = st.selectbox(
                "Scan Type",
                ["qr_code", "barcode"],
                key="sim_scan_type"
            )
            
            if st.button("🎯 Simulate Scan"):
                if sim_package_id != "No packages available":
                    result = tracker.simulate_package_scan(sim_package_id, sim_scan_type)
                    display_scan_result(result)


def render_ble_nfc_section(tracker):
    """Render BLE and NFC tracking section"""
    st.subheader("📡 BLE Beacon & NFC Tag Tracking")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Create BLE/NFC Tags")
        
        package_id = st.text_input("Package ID", value="PKG_BLE_001", key="ble_package_id")
        
        # BLE options
        st.write("**BLE Beacon Options:**")
        enable_ble = st.checkbox("Enable BLE Beacon", value=True)
        if enable_ble:
            ble_type = st.selectbox("Beacon Type", ["ibeacon", "eddystone"], key="ble_type")
            major = st.number_input("Major", value=1, min_value=0, max_value=65535, key="ble_major")
            minor = st.number_input("Minor", value=1, min_value=0, max_value=65535, key="ble_minor")
        
        # NFC options
        st.write("**NFC Tag Options:**")
        enable_nfc = st.checkbox("Enable NFC Tag", value=False)
        if enable_nfc:
            nfc_type = st.selectbox("Tag Type", ["ntag213", "ntag215", "ntag216"], key="nfc_type")
        
        if st.button("📡 Create BLE/NFC Tags"):
            if package_id:
                tracking_options = {
                    "enable_ble": enable_ble,
                    "enable_nfc": enable_nfc
                }
                
                if enable_ble:
                    tracking_options.update({
                        "ble_type": ble_type,
                        "ble_major": major,
                        "ble_minor": minor
                    })
                
                if enable_nfc:
                    tracking_options["nfc_type"] = nfc_type
                
                try:
                    journey = tracker.create_package_tracking(
                        package_id, f"ORD_{package_id}", tracking_options
                    )
                    
                    st.success(f"✅ Created BLE/NFC tags for {package_id}")
                    
                    # Display tag information
                    for tag in journey.tags:
                        if tag.tag_type.value == "ble_beacon":
                            st.info(f"🔵 BLE Beacon: {tag.tag_id}")
                        elif tag.tag_type.value == "nfc_tag":
                            st.info(f"🏷️ NFC Tag: {tag.tag_id}")
                
                except Exception as e:
                    st.error(f"❌ Error creating tags: {e}")
    
    with col2:
        st.write("### Proximity Detection")
        
        # BLE scanning
        st.write("**BLE Beacon Scanning:**")
        ble_packages = []
        for pkg_id, journey in tracker.packages.items():
            for tag in journey.tags:
                if tag.tag_type.value == "ble_beacon":
                    ble_packages.append(f"{pkg_id} ({tag.tag_id})")
        
        if ble_packages:
            selected_ble = st.selectbox("Select BLE Beacon", ble_packages, key="ble_scan_select")
            rssi = st.slider("RSSI (Signal Strength)", -100, -30, -65, key="ble_rssi")
            
            if st.button("📡 Simulate BLE Scan"):
                beacon_uuid = selected_ble.split('(')[1].strip(')')
                result = tracker.ble_nfc.scan_ble_beacon(beacon_uuid, rssi)
                display_scan_result(result)
        else:
            st.info("No BLE beacons available. Create some first!")
        
        # NFC scanning
        st.write("**NFC Tag Reading:**")
        nfc_packages = []
        for pkg_id, journey in tracker.packages.items():
            for tag in journey.tags:
                if tag.tag_type.value == "nfc_tag":
                    nfc_packages.append(f"{pkg_id} ({tag.tag_id})")
        
        if nfc_packages:
            selected_nfc = st.selectbox("Select NFC Tag", nfc_packages, key="nfc_scan_select")
            
            if st.button("🏷️ Simulate NFC Read"):
                tag_id = selected_nfc.split('(')[1].strip(')')
                result = tracker.ble_nfc.scan_nfc_tag(tag_id)
                display_scan_result(result)
        else:
            st.info("No NFC tags available. Create some first!")


def render_package_journey_section(tracker):
    """Render package journey tracking section"""
    st.subheader("🛣️ Package Journey Tracking")
    
    if not tracker.packages:
        st.info("No packages being tracked. Create some packages first!")
        return
    
    # Package selection
    selected_package = st.selectbox(
        "Select Package",
        list(tracker.packages.keys()),
        key="journey_package_select"
    )
    
    if selected_package:
        journey_data = tracker.get_package_journey(selected_package)
        
        if journey_data:
            col1, col2 = st.columns(2)
            
            with col1:
                # Package information
                st.write("### Package Information")
                st.metric("Package ID", journey_data["package_id"])
                st.metric("Tracking Number", journey_data["tracking_number"])
                st.metric("Order ID", journey_data["order_id"])
                st.metric("Status", journey_data["status"].upper())
                
                # Current location
                if journey_data["current_location"]:
                    location = journey_data["current_location"]
                    st.write(f"**Current Location:** {location.get('name', 'Unknown')}")
            
            with col2:
                # Tags information
                st.write("### Active Tags")
                for tag in journey_data["tags"]:
                    status_icon = "🟢" if tag["is_active"] else "🔴"
                    st.write(f"{status_icon} {tag['tag_type'].upper()} - Scans: {tag['scan_count']}")
            
            # Journey timeline
            st.write("### Journey Timeline")
            if journey_data["events"]:
                events_df = pd.DataFrame(journey_data["events"])
                events_df["timestamp"] = pd.to_datetime(events_df["timestamp"])
                
                # Create timeline visualization
                fig = px.timeline(
                    events_df,
                    x_start="timestamp",
                    x_end="timestamp",
                    y="status",
                    color="scan_type",
                    title="Package Journey Timeline"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Events table
                st.write("**Scan Events:**")
                display_df = events_df[["timestamp", "scan_type", "status", "scanner_id"]].copy()
                display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
                st.dataframe(display_df, use_container_width=True)
            else:
                st.info("No scan events recorded yet")


def render_batch_operations_section(tracker):
    """Render batch scanning operations section"""
    st.subheader("🎯 Batch Scanning Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Batch Code Input")
        
        batch_method = st.radio(
            "Input Method",
            ["Manual Entry", "File Upload"],
            key="batch_method"
        )
        
        scan_data_list = []
        
        if batch_method == "Manual Entry":
            batch_text = st.text_area(
                "Enter codes (one per line)",
                height=200,
                help="Enter QR codes or barcodes, one per line",
                key="batch_input"
            )
            
            if batch_text:
                lines = batch_text.strip().split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        scan_data_list.append({
                            "data": line.strip(),
                            "type": "auto",
                            "index": i + 1
                        })
        
        elif batch_method == "File Upload":
            uploaded_file = st.file_uploader(
                "Upload CSV file with codes",
                type=['csv'],
                key="batch_file"
            )
            
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    if "code" in df.columns:
                        for i, row in df.iterrows():
                            scan_data_list.append({
                                "data": str(row["code"]),
                                "type": row.get("type", "auto"),
                                "index": i + 1
                            })
                    else:
                        st.error("CSV file must have a 'code' column")
                except Exception as e:
                    st.error(f"Error reading file: {e}")
        
        if scan_data_list:
            st.info(f"📊 {len(scan_data_list)} codes ready for batch scanning")
            
            if st.button("🚀 Start Batch Scan"):
                with st.spinner("Processing batch scan..."):
                    results = tracker.qr_scanner.batch_scan(scan_data_list)
                    st.session_state.batch_results = results
                    st.success(f"✅ Batch scan completed: {len(results)} results")
    
    with col2:
        st.write("### Batch Results")
        
        if 'batch_results' in st.session_state:
            results = st.session_state.batch_results
            
            # Summary metrics
            successful = sum(1 for r in results if r.get("success"))
            failed = len(results) - successful
            
            col2a, col2b, col2c = st.columns(3)
            with col2a:
                st.metric("Total Scans", len(results))
            with col2b:
                st.metric("Successful", successful, delta=successful-failed)
            with col2c:
                st.metric("Success Rate", f"{successful/len(results)*100:.1f}%")
            
            # Results table
            results_df = pd.DataFrame([
                {
                    "Index": r.get("batch_info", {}).get("batch_index", 0) + 1,
                    "Success": "✅" if r.get("success") else "❌",
                    "Type": r.get("scan_type", "unknown"),
                    "Package ID": r.get("package_id") or r.get("data", {}).get("package_id", "N/A"),
                    "Error": r.get("error", "")
                }
                for r in results
            ])
            
            st.dataframe(results_df, use_container_width=True)
            
            # Download results
            csv_data = results_df.to_csv(index=False)
            st.download_button(
                "📥 Download Results CSV",
                csv_data,
                "batch_scan_results.csv",
                "text/csv"
            )
        else:
            st.info("No batch results yet. Run a batch scan to see results here.")


def render_tracking_analytics(tracker):
    """Render tracking analytics and statistics"""
    st.subheader("📈 Tracking Analytics & Statistics")
    
    # Get statistics
    stats = tracker.get_scanning_statistics()
    scanner_stats = tracker.qr_scanner.get_scanner_statistics() if hasattr(tracker.qr_scanner, 'get_scanner_statistics') else {}
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Packages", stats["total_packages"])
    with col2:
        st.metric("Total Scans", stats["total_scans"])
    with col3:
        st.metric("Active Tags", stats["active_tags"])
    with col4:
        st.metric("Avg Scans/Package", stats["average_scans_per_package"])
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Scan types distribution
        if stats["scan_types"]:
            scan_types_df = pd.DataFrame(
                list(stats["scan_types"].items()),
                columns=["Scan Type", "Count"]
            )
            
            fig = px.pie(
                scan_types_df,
                values="Count",
                names="Scan Type",
                title="Scan Types Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Package status distribution
        if stats["status_distribution"]:
            status_df = pd.DataFrame(
                list(stats["status_distribution"].items()),
                columns=["Status", "Count"]
            )
            
            fig = px.bar(
                status_df,
                x="Status",
                y="Count",
                title="Package Status Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Scanner performance
    if scanner_stats:
        st.write("### Scanner Performance")
        
        perf_col1, perf_col2, perf_col3 = st.columns(3)
        
        with perf_col1:
            st.metric("Success Rate", f"{scanner_stats.get('success_rate', 0):.1f}%")
        with perf_col2:
            st.metric("Avg Scan Time", f"{scanner_stats.get('average_scan_time_ms', 0):.1f} ms")
        with perf_col3:
            st.metric("Error Count", scanner_stats.get('error_count', 0))
    
    # Recent activity
    st.write("### Recent Scan Activity")
    if tracker.scan_events:
        recent_events = sorted(tracker.scan_events, key=lambda x: x.timestamp, reverse=True)[:10]
        
        recent_df = pd.DataFrame([
            {
                "Time": event.timestamp.strftime("%H:%M:%S"),
                "Package": event.package_id,
                "Type": event.scan_type.value,
                "Status": event.status.value,
                "Scanner": event.scanner_id
            }
            for event in recent_events
        ])
        
        st.dataframe(recent_df, use_container_width=True)
    else:
        st.info("No scan events recorded yet")


def display_scan_result(result):
    """Display scan result in a formatted way"""
    if result.get("success"):
        st.success("✅ Scan Successful!")
        
        # Create columns for result display
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Scan Information:**")
            st.write(f"- **Type:** {result.get('scan_type', 'Unknown')}")
            st.write(f"- **Scanner:** {result.get('scanner_id', 'Unknown')}")
            st.write(f"- **Time:** {result.get('timestamp', 'Unknown')}")
            
            if "quality_score" in result:
                st.write(f"- **Quality Score:** {result['quality_score']:.1f}%")
        
        with col2:
            st.write("**Package Data:**")
            package_data = result.get("data", {}) or result.get("package_data", {})
            package_id = result.get("package_id") or package_data.get("package_id")
            
            if package_id:
                st.write(f"- **Package ID:** {package_id}")
            
            # Additional data based on scan type
            if "distance_meters" in result:
                st.write(f"- **Distance:** {result['distance_meters']} m")
            if "proximity_zone" in result:
                st.write(f"- **Proximity:** {result['proximity_zone']}")
            if "format" in result:
                st.write(f"- **Format:** {result['format']}")
        
        # Show raw data
        with st.expander("Raw Scan Data"):
            st.json(result)
    
    else:
        st.error(f"❌ Scan Failed: {result.get('error', 'Unknown error')}")
        
        with st.expander("Error Details"):
            st.json(result)


if __name__ == "__main__":
    # For testing the dashboard components
    st.set_page_config(page_title="Package Tracking Demo", layout="wide")
    render_package_tracking_tab()