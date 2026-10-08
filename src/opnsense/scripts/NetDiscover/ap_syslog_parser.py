#!/usr/local/bin/python3
"""
WiFi AP Client Detection via Syslog Parsing
Parses AP syslog messages to discover client associations
"""

import re
import os
from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta


# Common syslog patterns for WiFi client events
CLIENT_PATTERNS = [
    # UniFi / Ubiquiti
    {
        'connect': r'(\w+): STA ([0-9a-fA-F:]{17}) associated',
        'disconnect': r'(\w+): STA ([0-9a-fA-F:]{17}) disassociated',
        'ap_group': 1, 'mac_group': 2
    },
    # TP-Link Omada
    {
        'connect': r'Client ([0-9a-fA-F:]{17}).*connected to ([^\s]+)',
        'disconnect': r'Client ([0-9a-fA-F:]{17}).*disconnected',
        'mac_group': 1, 'ap_group': 2
    },
    # OpenWrt / DD-WRT
    {
        'connect': r'hostapd.*AP-([^\s]+).*STA ([0-9a-fA-F:]{17}) IEEE 802.11: associated',
        'disconnect': r'hostapd.*AP-([^\s]+).*STA ([0-9a-fA-F:]{17}) IEEE 802.11: disassociated',
        'ap_group': 1, 'mac_group': 2
    },
    # MikroTik
    {
        'connect': r'wireless,info ([^\s]+) connected, ([0-9A-F:]{17})',
        'mac_group': 2, 'ap_group': 1
    },
    # Generic hostapd
    {
        'connect': r'hostapd.*STA ([0-9a-fA-F:]{17}).*associated',
        'mac_group': 1
    },
    # AsusWRT / Merlin
    {
        'connect': r'WLAN access accepted: ([0-9a-fA-F:]{17})',
        'disconnect': r'WLAN access rejected: ([0-9a-fA-F:]{17})',
        'mac_group': 1
    }
]


def parse_syslog_file(filepath: str, hours_back: int = 24) -> Dict[str, Tuple[str, int]]:
    """
    Parse syslog file for WiFi client associations.
    Returns: {client_mac: (ap_identifier, timestamp)}
    Only returns connections from last N hours.
    """
    client_associations = {}
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    if not os.path.exists(filepath):
        return client_associations
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Try to extract timestamp (various formats)
                line_time = extract_timestamp(line)
                if line_time and line_time < cutoff_time:
                    continue  # Skip old entries
                
                # Try each pattern
                for pattern_set in CLIENT_PATTERNS:
                    connect_pattern = pattern_set.get('connect')
                    if not connect_pattern:
                        continue
                    
                    match = re.search(connect_pattern, line, re.IGNORECASE)
                    if match:
                        mac_group = pattern_set.get('mac_group', 1)
                        ap_group = pattern_set.get('ap_group', 0)
                        
                        try:
                            client_mac = match.group(mac_group).upper().replace('-', ':')
                            ap_id = match.group(ap_group) if ap_group > 0 else 'unknown'
                            
                            # Validate MAC format
                            if re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', client_mac):
                                timestamp = int(line_time.timestamp()) if line_time else 0
                                # Keep most recent association for each client
                                if client_mac not in client_associations or timestamp > client_associations[client_mac][1]:
                                    client_associations[client_mac] = (ap_id, timestamp)
                        except (IndexError, AttributeError):
                            continue
    except Exception:
        pass
    
    return client_associations


def extract_timestamp(line: str) -> datetime:
    """
    Extract timestamp from syslog line.
    Handles multiple formats.
    """
    # BSD syslog: Dec 27 10:15:30
    match = re.match(r'([A-Z][a-z]{2})\s+(\d+)\s+(\d{2}):(\d{2}):(\d{2})', line)
    if match:
        try:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            month = month_names.index(match.group(1)) + 1
            day = int(match.group(2))
            hour = int(match.group(3))
            minute = int(match.group(4))
            second = int(match.group(5))
            
            # Use current year
            year = datetime.now().year
            return datetime(year, month, day, hour, minute, second)
        except:
            pass
    
    # ISO format: 2025-12-27T10:15:30
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})', line)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                          int(match.group(4)), int(match.group(5)), int(match.group(6)))
        except:
            pass
    
    return None


def parse_multiple_syslogs(syslog_paths: List[str] = None, hours_back: int = 24) -> Dict[str, Tuple[str, int]]:
    """
    Parse multiple syslog files (current + rotated).
    Returns: Combined client associations from all logs
    """
    if syslog_paths is None:
        # Common syslog locations
        syslog_paths = [
            '/var/log/messages',
            '/var/log/syslog',
            '/var/log/system.log',
            '/var/log/messages.0',  # Rotated logs
            '/var/log/messages.1',
        ]
    
    all_associations = {}
    
    for path in syslog_paths:
        associations = parse_syslog_file(path, hours_back)
        # Merge, keeping most recent timestamp for each client
        for mac, (ap_id, timestamp) in associations.items():
            if mac not in all_associations or timestamp > all_associations[mac][1]:
                all_associations[mac] = (ap_id, timestamp)
    
    return all_associations


def resolve_ap_identifier(ap_id: str, known_aps: Dict[str, str]) -> str:
    """
    Resolve AP identifier from syslog to actual AP IP or hostname.
    ap_id: Identifier from syslog (interface name, hostname fragment, etc.)
    known_aps: {ip: hostname} dict of known APs
    Returns: Best match IP or original identifier
    """
    ap_id_lower = ap_id.lower()
    
    # Try exact hostname match
    for ip, hostname in known_aps.items():
        if hostname and hostname.lower() == ap_id_lower:
            return ip
    
    # Try partial hostname match
    for ip, hostname in known_aps.items():
        if hostname and ap_id_lower in hostname.lower():
            return ip
    
    # Try if ap_id looks like an IP
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ap_id):
        return ap_id
    
    # Return original if no match
    return ap_id


if __name__ == '__main__':
    # Test/demo
    associations = parse_multiple_syslogs()
    print(f"Found {len(associations)} client associations from syslog:")
    for mac, (ap_id, timestamp) in sorted(associations.items(), key=lambda x: x[1][1], reverse=True):
        time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'unknown'
        print(f"  {mac} → {ap_id} (at {time_str})")

