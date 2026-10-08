#!/usr/local/bin/python3
"""
WiFi Access Point Client Detection
Queries APs via SNMP to discover which clients are connected to which AP
"""

import subprocess
import re
from typing import Dict, List, Tuple


# Common SNMP OIDs for wireless client tables
SNMP_CLIENT_OIDS = {
    'mikrotik': '1.3.6.1.4.1.14988.1.1.1.2.1.1',  # Wireless registration table
    'ubiquiti': '1.3.6.1.4.1.41112.1.6.1.2.1.6',   # UniFi client MAC
    'cisco': '1.3.6.1.4.1.9.9.273.1.1.2.1.1',       # Cisco client table
    'aruba': '1.3.6.1.4.1.14823.2.2.1.5.2.1.5.1.3', # Aruba client MAC
    'generic': '1.3.6.1.2.1.17.4.3.1.1'             # Bridge table (fallback)
}


def snmpwalk(ip: str, community: str, oid: str, timeout_ms: int = 1000) -> List[str]:
    """
    Execute snmpwalk command and return results.
    Returns: List of OID = value strings
    """
    timeout_sec = timeout_ms / 1000.0
    
    try:
        cmd = [
            'snmpwalk',
            '-v', '2c',
            '-c', community,
            '-t', str(timeout_sec),
            '-r', '0',  # No retries
            ip,
            oid
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout_sec + 1,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip().split('\n')
        
    except Exception:
        pass
    
    return []


def parse_mac_from_snmp(line: str) -> str:
    """
    Extract MAC address from SNMP response line.
    Handles various formats:
    - Hex string: 0x AABBCCDDEEFF
    - Colon format: AA:BB:CC:DD:EE:FF
    - OID index: ...1.170.187.204.221.238.255
    """
    mac = ''
    
    # Try hex string format
    hex_match = re.search(r'0x\s*([0-9A-Fa-f]{12})', line)
    if hex_match:
        hex_str = hex_match.group(1)
        mac = ':'.join([hex_str[i:i+2] for i in range(0, 12, 2)])
        return mac.upper()
    
    # Try colon format
    colon_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', line)
    if colon_match:
        return colon_match.group(1).upper()
    
    # Try OID index (6 decimal bytes)
    oid_match = re.search(r'\.(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\s*=', line)
    if oid_match:
        bytes_list = [int(oid_match.group(i)) for i in range(1, 7)]
        if all(0 <= b <= 255 for b in bytes_list):
            mac = ':'.join([f'{b:02X}' for b in bytes_list])
            return mac
    
    return ''


def query_ap_clients(ap_ip: str, community: str = 'public', timeout_ms: int = 2000) -> List[str]:
    """
    Query an AP for connected clients.
    Returns: List of client MAC addresses
    """
    clients = []
    
    # Try each OID type
    for vendor, oid in SNMP_CLIENT_OIDS.items():
        results = snmpwalk(ap_ip, community, oid, timeout_ms)
        
        if results:
            for line in results:
                mac = parse_mac_from_snmp(line)
                if mac and mac not in clients:
                    clients.append(mac)
        
        # If we found clients, stop trying other OIDs
        if clients:
            break
    
    return clients


def discover_ap_clients(ap_list: List[Dict], communities: List[str] = ['public']) -> Dict[str, str]:
    """
    Query all APs and build MAC → AP mapping.
    ap_list: List of dicts with 'ip' and optionally 'hostname'
    Returns: {client_mac: ap_ip}
    """
    client_to_ap = {}
    
    for ap in ap_list:
        ap_ip = ap.get('ip')
        if not ap_ip:
            continue
        
        # Try each community string
        for community in communities:
            clients = query_ap_clients(ap_ip, community)
            
            if clients:
                # Map each client to this AP
                for client_mac in clients:
                    client_to_ap[client_mac] = ap_ip
                break  # Community worked, stop trying others
    
    return client_to_ap


if __name__ == '__main__':
    # Test/demo
    import sys
    if len(sys.argv) > 1:
        ap_ip = sys.argv[1]
        community = sys.argv[2] if len(sys.argv) > 2 else 'public'
        
        clients = query_ap_clients(ap_ip, community)
        print(f"AP {ap_ip} has {len(clients)} connected clients:")
        for mac in clients:
            print(f"  - {mac}")
    else:
        print("Usage: python3 ap_detector.py <ap_ip> [community]")

