"""
QR Code and Barcode Scanner Implementation

This module provides QR code and barcode generation/scanning capabilities
with support for various barcode formats and validation mechanisms.
"""

import json
import time
import hashlib
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from enum import Enum
import re

from loguru import logger


class BarcodeFormat(Enum):
    """Supported barcode formats"""
    CODE128 = "code128"
    CODE39 = "code39"
    EAN13 = "ean13"
    EAN8 = "ean8"
    UPC_A = "upc_a"
    QR_CODE = "qr_code"
    DATAMATRIX = "datamatrix"


class ScannerCapability(Enum):
    """Scanner capability types"""
    QR_CODE = "qr_code"
    BARCODE_1D = "barcode_1d"
    BARCODE_2D = "barcode_2d"
    BATCH_SCAN = "batch_scan"
    CONTINUOUS_SCAN = "continuous_scan"


class BarcodeScanner:
    """Advanced barcode and QR code scanner implementation"""
    
    def __init__(self, scanner_id: str = None):
        self.scanner_id = scanner_id or f"SCANNER_{uuid.uuid4().hex[:8].upper()}"
        self.capabilities = [
            ScannerCapability.QR_CODE,
            ScannerCapability.BARCODE_1D,
            ScannerCapability.BARCODE_2D,
            ScannerCapability.BATCH_SCAN
        ]
        self.scan_history = []
        self.error_count = 0
        self.total_scans = 0
        
        logger.info(f"Initialized barcode scanner: {self.scanner_id}")
    
    def generate_qr_code(self, data: Dict, error_correction: str = "M") -> Dict:
        """
        Generate QR code with embedded data and validation
        
        Args:
            data: Dictionary containing package/tracking information
            error_correction: Error correction level (L, M, Q, H)
        
        Returns:
            Dictionary with QR code data and metadata
        """
        try:
            # Add metadata and validation
            qr_payload = {
                "version": "1.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "scanner_id": self.scanner_id,
                "data": data,
                "checksum": self._calculate_checksum(json.dumps(data, sort_keys=True))
            }
            
            # Encode as base64 JSON
            json_str = json.dumps(qr_payload, sort_keys=True)
            qr_code_data = base64.b64encode(json_str.encode()).decode()
            
            qr_info = {
                "qr_code": qr_code_data,
                "format": BarcodeFormat.QR_CODE.value,
                "size_bytes": len(qr_code_data),
                "error_correction": error_correction,
                "estimated_modules": self._estimate_qr_modules(len(json_str)),
                "generated_at": datetime.now(timezone.utc),
                "expires_at": None,  # QR codes don't expire by default
                "metadata": {
                    "data_type": "logistics_tracking",
                    "encoding": "base64_json",
                    "version": "1.0"
                }
            }
            
            logger.debug(f"Generated QR code with {qr_info['size_bytes']} bytes")
            return qr_info
            
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")
            raise ValueError(f"Failed to generate QR code: {e}")
    
    def generate_barcode(self, package_id: str, format_type: BarcodeFormat = BarcodeFormat.CODE128, 
                        include_check_digit: bool = True) -> Dict:
        """
        Generate barcode with specified format
        
        Args:
            package_id: Package identifier
            format_type: Barcode format to generate
            include_check_digit: Whether to include check digit
        
        Returns:
            Dictionary with barcode data and metadata
        """
        try:
            timestamp = int(time.time())
            
            if format_type == BarcodeFormat.CODE128:
                # Code 128 can encode alphanumeric
                barcode_data = f"{package_id}#{timestamp}"
                if include_check_digit:
                    check_digit = self._calculate_code128_check_digit(barcode_data)
                    barcode_data += f"#{check_digit}"
                    
            elif format_type == BarcodeFormat.CODE39:
                # Code 39 limited character set
                clean_id = re.sub(r'[^A-Z0-9\-. $/+%]', '', package_id.upper())
                barcode_data = f"{clean_id}-{timestamp}"
                if include_check_digit:
                    check_digit = self._calculate_code39_check_digit(barcode_data)
                    barcode_data += f"-{check_digit}"
                    
            elif format_type == BarcodeFormat.EAN13:
                # EAN-13 requires 13 digits
                numeric_id = ''.join(filter(str.isdigit, package_id))[:12]
                if len(numeric_id) < 12:
                    numeric_id = numeric_id.ljust(12, '0')
                barcode_data = numeric_id
                if include_check_digit:
                    check_digit = self._calculate_ean13_check_digit(numeric_id)
                    barcode_data += str(check_digit)
                    
            else:
                # Generic format
                barcode_data = f"{package_id}_{timestamp}"
            
            barcode_info = {
                "barcode": barcode_data,
                "format": format_type.value,
                "package_id": package_id,
                "includes_check_digit": include_check_digit,
                "length": len(barcode_data),
                "generated_at": datetime.now(timezone.utc),
                "scanner_compatible": True,
                "metadata": {
                    "original_package_id": package_id,
                    "timestamp": timestamp,
                    "format_spec": format_type.value
                }
            }
            
            logger.debug(f"Generated {format_type.value} barcode: {barcode_data}")
            return barcode_info
            
        except Exception as e:
            logger.error(f"Barcode generation failed: {e}")
            raise ValueError(f"Failed to generate barcode: {e}")
    
    def scan_qr_code(self, qr_data: str, validate_checksum: bool = True) -> Dict:
        """
        Scan and decode QR code data
        
        Args:
            qr_data: QR code data string
            validate_checksum: Whether to validate data integrity
        
        Returns:
            Scan result dictionary
        """
        scan_start = time.time()
        
        try:
            self.total_scans += 1
            
            # Decode base64 JSON
            try:
                json_str = base64.b64decode(qr_data.encode()).decode()
                qr_payload = json.loads(json_str)
            except Exception:
                raise ValueError("Invalid QR code format or corrupted data")
            
            # Validate structure
            required_fields = ["version", "data", "checksum"]
            for field in required_fields:
                if field not in qr_payload:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate checksum if requested
            if validate_checksum:
                expected_checksum = self._calculate_checksum(
                    json.dumps(qr_payload["data"], sort_keys=True)
                )
                if qr_payload["checksum"] != expected_checksum:
                    raise ValueError("QR code checksum validation failed")
            
            scan_result = {
                "success": True,
                "scan_type": "qr_code",
                "scanner_id": self.scanner_id,
                "data": qr_payload["data"],
                "metadata": {
                    "qr_version": qr_payload.get("version"),
                    "generated_at": qr_payload.get("generated_at"),
                    "original_scanner": qr_payload.get("scanner_id"),
                    "scan_duration_ms": round((time.time() - scan_start) * 1000, 2),
                    "checksum_validated": validate_checksum
                },
                "timestamp": datetime.now(timezone.utc),
                "quality_score": self._assess_scan_quality(qr_data)
            }
            
            self.scan_history.append(scan_result)
            logger.info(f"Successfully scanned QR code for package {qr_payload['data'].get('package_id', 'unknown')}")
            
            return scan_result
            
        except Exception as e:
            self.error_count += 1
            error_result = {
                "success": False,
                "scan_type": "qr_code",
                "scanner_id": self.scanner_id,
                "error": str(e),
                "error_code": self._classify_error(str(e)),
                "timestamp": datetime.now(timezone.utc),
                "scan_duration_ms": round((time.time() - scan_start) * 1000, 2)
            }
            
            self.scan_history.append(error_result)
            logger.error(f"QR code scan failed: {e}")
            
            return error_result
    
    def scan_barcode(self, barcode_data: str, expected_format: BarcodeFormat = None,
                    validate_check_digit: bool = True) -> Dict:
        """
        Scan and decode barcode data
        
        Args:
            barcode_data: Barcode data string
            expected_format: Expected barcode format for validation
            validate_check_digit: Whether to validate check digit
        
        Returns:
            Scan result dictionary
        """
        scan_start = time.time()
        
        try:
            self.total_scans += 1
            
            # Detect format if not specified
            detected_format = expected_format or self._detect_barcode_format(barcode_data)
            
            # Parse barcode based on format
            if detected_format == BarcodeFormat.CODE128:
                parse_result = self._parse_code128(barcode_data, validate_check_digit)
            elif detected_format == BarcodeFormat.CODE39:
                parse_result = self._parse_code39(barcode_data, validate_check_digit)
            elif detected_format == BarcodeFormat.EAN13:
                parse_result = self._parse_ean13(barcode_data, validate_check_digit)
            else:
                # Generic parsing
                parse_result = self._parse_generic_barcode(barcode_data)
            
            if not parse_result["valid"]:
                raise ValueError(parse_result["error"])
            
            scan_result = {
                "success": True,
                "scan_type": "barcode",
                "scanner_id": self.scanner_id,
                "barcode": barcode_data,
                "format": detected_format.value,
                "package_id": parse_result["package_id"],
                "metadata": {
                    "format_detected": detected_format.value,
                    "check_digit_valid": parse_result.get("check_digit_valid", None),
                    "scan_duration_ms": round((time.time() - scan_start) * 1000, 2),
                    "parse_metadata": parse_result.get("metadata", {})
                },
                "timestamp": datetime.now(timezone.utc),
                "quality_score": self._assess_scan_quality(barcode_data)
            }
            
            self.scan_history.append(scan_result)
            logger.info(f"Successfully scanned {detected_format.value} barcode for package {parse_result['package_id']}")
            
            return scan_result
            
        except Exception as e:
            self.error_count += 1
            error_result = {
                "success": False,
                "scan_type": "barcode",
                "scanner_id": self.scanner_id,
                "barcode": barcode_data,
                "error": str(e),
                "error_code": self._classify_error(str(e)),
                "timestamp": datetime.now(timezone.utc),
                "scan_duration_ms": round((time.time() - scan_start) * 1000, 2)
            }
            
            self.scan_history.append(error_result)
            logger.error(f"Barcode scan failed: {e}")
            
            return error_result
    
    def batch_scan(self, scan_data_list: List[Dict]) -> List[Dict]:
        """
        Perform batch scanning of multiple codes
        
        Args:
            scan_data_list: List of dictionaries with 'data' and 'type' keys
        
        Returns:
            List of scan results
        """
        batch_start = time.time()
        results = []
        
        logger.info(f"Starting batch scan of {len(scan_data_list)} items")
        
        for i, scan_item in enumerate(scan_data_list):
            try:
                data = scan_item["data"]
                scan_type = scan_item.get("type", "auto")
                
                if scan_type == "qr_code" or (scan_type == "auto" and self._looks_like_qr_data(data)):
                    result = self.scan_qr_code(data)
                else:
                    result = self.scan_barcode(data)
                
                # Add batch metadata
                result["batch_info"] = {
                    "batch_index": i,
                    "batch_size": len(scan_data_list),
                    "batch_id": f"BATCH_{int(time.time())}"
                }
                
                results.append(result)
                
            except Exception as e:
                error_result = {
                    "success": False,
                    "error": str(e),
                    "batch_info": {
                        "batch_index": i,
                        "batch_size": len(scan_data_list),
                        "failed_item": scan_item
                    }
                }
                results.append(error_result)
        
        batch_duration = time.time() - batch_start
        successful_scans = sum(1 for r in results if r.get("success"))
        
        logger.info(f"Batch scan completed: {successful_scans}/{len(scan_data_list)} successful in {batch_duration:.2f}s")
        
        return results
    
    def get_scanner_statistics(self) -> Dict:
        """Get scanner performance statistics"""
        successful_scans = sum(1 for scan in self.scan_history if scan.get("success"))
        
        if self.scan_history:
            avg_scan_time = sum(
                scan.get("metadata", {}).get("scan_duration_ms", 0) 
                for scan in self.scan_history
            ) / len(self.scan_history)
            
            scan_types = {}
            for scan in self.scan_history:
                scan_type = scan.get("scan_type", "unknown")
                scan_types[scan_type] = scan_types.get(scan_type, 0) + 1
        else:
            avg_scan_time = 0
            scan_types = {}
        
        return {
            "scanner_id": self.scanner_id,
            "total_scans": self.total_scans,
            "successful_scans": successful_scans,
            "error_count": self.error_count,
            "success_rate": round(successful_scans / max(self.total_scans, 1) * 100, 2),
            "average_scan_time_ms": round(avg_scan_time, 2),
            "scan_types": scan_types,
            "capabilities": [cap.value for cap in self.capabilities],
            "last_scan": self.scan_history[-1]["timestamp"].isoformat() if self.scan_history else None
        }
    
    # Helper methods for barcode generation and parsing
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate MD5 checksum for data validation"""
        return hashlib.md5(data.encode()).hexdigest()
    
    def _calculate_code128_check_digit(self, data: str) -> str:
        """Calculate Code 128 check digit"""
        # Simplified check digit calculation
        checksum = sum(ord(c) for c in data) % 103
        return str(checksum)
    
    def _calculate_code39_check_digit(self, data: str) -> str:
        """Calculate Code 39 check digit"""
        # Simplified modulo 43 check digit
        char_values = {chr(i): i for i in range(48, 58)}  # 0-9
        char_values.update({chr(i): i - 55 for i in range(65, 91)})  # A-Z
        
        total = sum(char_values.get(c, 0) for c in data.upper())
        return str(total % 43)
    
    def _calculate_ean13_check_digit(self, data: str) -> int:
        """Calculate EAN-13 check digit"""
        odd_sum = sum(int(data[i]) for i in range(0, 12, 2))
        even_sum = sum(int(data[i]) for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        return (10 - (total % 10)) % 10
    
    def _estimate_qr_modules(self, data_length: int) -> int:
        """Estimate QR code modules based on data length"""
        # Simplified estimation
        if data_length <= 25:
            return 21  # Version 1
        elif data_length <= 47:
            return 25  # Version 2
        elif data_length <= 77:
            return 29  # Version 3
        else:
            return 33  # Version 4+
    
    def _detect_barcode_format(self, barcode_data: str) -> BarcodeFormat:
        """Detect barcode format from data pattern"""
        if barcode_data.isdigit():
            if len(barcode_data) == 13:
                return BarcodeFormat.EAN13
            elif len(barcode_data) == 8:
                return BarcodeFormat.EAN8
            elif len(barcode_data) == 12:
                return BarcodeFormat.UPC_A
        
        if re.match(r'^[A-Z0-9\-. $/+%]+$', barcode_data):
            return BarcodeFormat.CODE39
        
        return BarcodeFormat.CODE128  # Default to most flexible format
    
    def _parse_code128(self, barcode_data: str, validate_check_digit: bool) -> Dict:
        """Parse Code 128 barcode"""
        parts = barcode_data.split('#')
        
        if len(parts) >= 2:
            package_id = parts[0]
            timestamp = parts[1] if len(parts) > 1 else None
            check_digit = parts[2] if len(parts) > 2 else None
            
            if validate_check_digit and check_digit:
                expected_check = self._calculate_code128_check_digit('#'.join(parts[:-1]))
                check_valid = (check_digit == expected_check)
            else:
                check_valid = None
            
            return {
                "valid": True,
                "package_id": package_id,
                "check_digit_valid": check_valid,
                "metadata": {"timestamp": timestamp}
            }
        
        return {"valid": False, "error": "Invalid Code 128 format"}
    
    def _parse_code39(self, barcode_data: str, validate_check_digit: bool) -> Dict:
        """Parse Code 39 barcode"""
        parts = barcode_data.split('-')
        
        if len(parts) >= 2:
            package_id = parts[0]
            timestamp = parts[1] if len(parts) > 1 else None
            check_digit = parts[2] if len(parts) > 2 else None
            
            if validate_check_digit and check_digit:
                expected_check = self._calculate_code39_check_digit('-'.join(parts[:-1]))
                check_valid = (check_digit == expected_check)
            else:
                check_valid = None
            
            return {
                "valid": True,
                "package_id": package_id,
                "check_digit_valid": check_valid,
                "metadata": {"timestamp": timestamp}
            }
        
        return {"valid": False, "error": "Invalid Code 39 format"}
    
    def _parse_ean13(self, barcode_data: str, validate_check_digit: bool) -> Dict:
        """Parse EAN-13 barcode"""
        if len(barcode_data) != 13 or not barcode_data.isdigit():
            return {"valid": False, "error": "Invalid EAN-13 format"}
        
        data_digits = barcode_data[:12]
        check_digit = int(barcode_data[12])
        
        if validate_check_digit:
            expected_check = self._calculate_ean13_check_digit(data_digits)
            check_valid = (check_digit == expected_check)
        else:
            check_valid = None
        
        return {
            "valid": True,
            "package_id": data_digits,  # Use first 12 digits as package ID
            "check_digit_valid": check_valid,
            "metadata": {"ean13_format": True}
        }
    
    def _parse_generic_barcode(self, barcode_data: str) -> Dict:
        """Parse generic barcode format"""
        # Split on common delimiters
        for delimiter in ['_', '-', '#', '|']:
            if delimiter in barcode_data:
                parts = barcode_data.split(delimiter)
                return {
                    "valid": True,
                    "package_id": parts[0],
                    "metadata": {"delimiter": delimiter, "parts": parts}
                }
        
        # Use entire string as package ID
        return {
            "valid": True,
            "package_id": barcode_data,
            "metadata": {"format": "single_string"}
        }
    
    def _looks_like_qr_data(self, data: str) -> bool:
        """Heuristic to determine if data looks like QR code data"""
        # QR codes are typically longer and contain base64-like characters
        return (len(data) > 50 and 
                any(c in data for c in ['+', '/', '=']) and
                not data.replace('+', '').replace('/', '').replace('=', '').isdigit())
    
    def _assess_scan_quality(self, data: str) -> float:
        """Assess scan quality based on data characteristics"""
        quality = 100.0
        
        # Penalize very short or very long data
        if len(data) < 5:
            quality -= 30
        elif len(data) > 1000:
            quality -= 10
        
        # Penalize unusual character patterns
        if len(set(data)) < 3:  # Very low character diversity
            quality -= 20
        
        # Bonus for structured data
        if any(delimiter in data for delimiter in ['#', '-', '_', '|']):
            quality += 10
        
        return max(0.0, min(100.0, quality))
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type for better debugging"""
        error_msg = error_message.lower()
        
        if "checksum" in error_msg or "validation" in error_msg:
            return "VALIDATION_ERROR"
        elif "format" in error_msg or "invalid" in error_msg:
            return "FORMAT_ERROR"
        elif "corrupted" in error_msg or "decode" in error_msg:
            return "DATA_CORRUPTION"
        elif "missing" in error_msg:
            return "MISSING_DATA"
        else:
            return "UNKNOWN_ERROR"


if __name__ == "__main__":
    # Demo usage
    scanner = BarcodeScanner()
    
    # Generate and scan QR code
    qr_info = scanner.generate_qr_code({"package_id": "PKG_DEMO_001", "order_id": "ORD_001"})
    qr_result = scanner.scan_qr_code(qr_info["qr_code"])
    
    # Generate and scan barcode
    barcode_info = scanner.generate_barcode("PKG_DEMO_002", BarcodeFormat.CODE128)
    barcode_result = scanner.scan_barcode(barcode_info["barcode"])
    
    # Print statistics
    stats = scanner.get_scanner_statistics()
    print("Scanner Statistics:", json.dumps(stats, indent=2, default=str))