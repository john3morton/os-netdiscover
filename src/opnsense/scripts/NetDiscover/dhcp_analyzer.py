#!/usr/local/bin/python3
"""
DHCP Type Analyzer
Determines if IP addresses are static, reserved, or dynamic based on dnsmasq configuration
"""

import re
import os
from typing import Dict, Set, Tuple
from ipaddress import ip_address, ip_network


def parse_dnsmasq_config() -> Tuple[Set, Dict]:
    """
    Parse dnsmasq configuration to find DHCP ranges and reservations.
    Returns: (dhcp_ranges, mac_reservations)
    """
    dhcp_ranges = set()  # Set of (start_ip, end_ip) tuples
    mac_reservations = {}  # {ip: mac} for reserved addresses
    
    config_paths = [
        '/var/etc/dnsmasq.conf',
        '/usr/local/etc/dnsmasq.conf',
        '/etc/dnsmasq.conf'
    ]
    
    for path in config_paths:
        if not os.path.exists(path):
            continue
        
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    
                    # dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
                    if line.startswith('dhcp-range='):
                        parts = line.split('=', 1)[1].split(',')
                        if len(parts) >= 2:
                            start_ip = parts[0].strip()
                            end_ip = parts[1].strip()
                            dhcp_ranges.add((start_ip, end_ip))
                    
                    # dhcp-host=aa:bb:cc:dd:ee:ff,192.168.1.50,hostname
                    elif line.startswith('dhcp-host='):
                        parts = line.split('=', 1)[1].split(',')
                        if len(parts) >= 2:
                            mac = parts[0].strip()
                            ip = parts[1].strip()
                            # Validate IP format
                            try:
                                ip_address(ip)
                                mac_reservations[ip] = mac
                            except:
                                pass
        except Exception:
            continue
    
    return dhcp_ranges, mac_reservations


def parse_dnsmasq_leases() -> Dict:
    """
    Parse dnsmasq lease file to find active DHCP leases.
    Returns: {ip: {'mac': mac, 'hostname': hostname, 'expires': timestamp}}
    """
    leases = {}
    lease_file = '/var/db/dhcpd.leases'
    
    if not os.path.exists(lease_file):
        return leases
    
    try:
        with open(lease_file, 'r') as f:
            for line in f:
                # Format: timestamp mac ip hostname client_id
                # Example: 1703622000 aa:bb:cc:dd:ee:ff 192.168.1.100 hostname *
                parts = line.strip().split()
                if len(parts) >= 4:
                    timestamp = parts[0]
                    mac = parts[1]
                    ip = parts[2]
                    hostname = parts[3]
                    leases[ip] = {
                        'mac': mac,
                        'hostname': hostname,
                        'expires': timestamp
                    }
    except Exception:
        pass
    
    return leases


def determine_dhcp_type(ip_str: str) -> str:
    """
    Determine if an IP is static, reserved, or dynamic.
    Returns: 'static' | 'reserved' | 'dynamic' | 'unknown'
    """
    dhcp_ranges, mac_reservations = parse_dnsmasq_config()
    leases = parse_dnsmasq_leases()
    
    # Check if IP is a reservation
    if ip_str in mac_reservations:
        return 'reserved'
    
    # Check if IP is in any DHCP range
    try:
        ip_obj = ip_address(ip_str)
        
        in_dhcp_range = False
        for start_ip, end_ip in dhcp_ranges:
            try:
                start = ip_address(start_ip)
                end = ip_address(end_ip)
                if start <= ip_obj <= end:
                    in_dhcp_range = True
                    break
            except:
                continue
        
        if in_dhcp_range:
            # In DHCP range - check if it has an active lease
            if ip_str in leases:
                return 'dynamic'
            else:
                # In range but no lease - might be reserved or not yet leased
                return 'unknown'
        else:
            # Outside DHCP range - static
            return 'static'
    except:
        return 'unknown'


def get_dhcp_info_batch(ip_list: list) -> Dict[str, str]:
    """
    Get DHCP type for multiple IPs in batch (more efficient).
    Returns: {ip: dhcp_type}
    """
    # Parse config once
    dhcp_ranges, mac_reservations = parse_dnsmasq_config()
    leases = parse_dnsmasq_leases()
    
    result = {}
    for ip_str in ip_list:
        # Check reservation
        if ip_str in mac_reservations:
            result[ip_str] = 'reserved'
            continue
        
        # Check range
        try:
            ip_obj = ip_address(ip_str)
            in_range = False
            
            for start_ip, end_ip in dhcp_ranges:
                try:
                    if ip_address(start_ip) <= ip_obj <= ip_address(end_ip):
                        in_range = True
                        break
                except:
                    continue
            
            if in_range:
                result[ip_str] = 'dynamic' if ip_str in leases else 'unknown'
            else:
                result[ip_str] = 'static'
        except:
            result[ip_str] = 'unknown'
    
    return result


if __name__ == '__main__':
    # Test/demo
    import sys
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        dhcp_type = determine_dhcp_type(ip)
        print(f"{ip}: {dhcp_type}")
    else:
        print("Usage: python3 dhcp_analyzer.py <ip_address>")

