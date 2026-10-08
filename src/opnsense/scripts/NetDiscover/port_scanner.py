#!/usr/local/bin/python3
"""
Simple TCP port scanner (fallback if nmap not available)
Usage: port_scanner.py <ip> <start_port> <end_port>
Output: JSON array of open ports
"""

import socket
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


def scan_port(ip, port, timeout=0.3):
    """Check if a single port is open (v1.7.2: faster timeout for 65K scan)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return port if result == 0 else None
    except:
        return None


def scan_ports(ip, start_port, end_port, max_workers=200):
    """
    Scan a range of ports using thread pool.
    v1.7.2: Increased max_workers to 200 for faster 65K scans (5-7 minutes typical).
    """
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_port, ip, port): port 
                  for port in range(start_port, end_port + 1)}
        
        for future in as_completed(futures):
            result = future.result()
            if result:
                open_ports.append(result)
    
    return sorted(open_ports)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(json.dumps([]), file=sys.stderr)
        sys.exit(1)
    
    ip = sys.argv[1]
    start_port = int(sys.argv[2])
    end_port = int(sys.argv[3])
    
    open_ports = scan_ports(ip, start_port, end_port)
    print(json.dumps(open_ports))

