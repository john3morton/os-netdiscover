#!/usr/local/bin/python3
"""
Device Fingerprinting Patterns
Pattern-based device type and model identification
"""

import re
from typing import Optional, Dict, Set, List, Tuple


def guess_device_type_from_hostname(hostname: str) -> Optional[str]:
    """Infer device type from hostname patterns"""
    if not hostname:
        return None
    
    h = hostname.lower()
    
    # Mobile devices
    if h.startswith('android-') or 'android' in h:
        return 'Android Phone/Tablet'
    if h.startswith('iphone'):
        return 'iPhone'
    if h.startswith('ipad'):
        return 'iPad'
    if h.startswith('galaxy-'):
        return 'Samsung Galaxy'
    
    # Apple devices
    if h.startswith('macbook'):
        return 'MacBook'
    if h.startswith('imac'):
        return 'iMac'
    if 'apple-tv' in h or h.startswith('appletv'):
        return 'Apple TV'
    
    # IoT/Embedded
    if 'esp_' in h or 'esp-' in h or 'esp8266' in h or 'esp32' in h:
        return 'ESP32/ESP8266 IoT'
    if 'raspberry' in h or 'raspi' in h:
        return 'Raspberry Pi'
    if 'arduino' in h:
        return 'Arduino'
    if 'tasmota' in h:
        return 'Tasmota Device'
    if 'shelly' in h:
        return 'Shelly Smart Device'
    
    # Printers
    if any(x in h for x in ['printer', 'print', 'laserjet', 'inkjet', 'officejet']):
        return 'Printer'
    if re.search(r'\bhp\w*\d+', h):  # HP followed by model number
        return 'HP Printer'
    if any(x in h for x in ['canon', 'epson', 'brother', 'xerox']):
        return 'Printer'
    
    # NAS/Storage
    if 'nas' in h or 'synology' in h or 'qnap' in h:
        return 'NAS'
    if 'diskstation' in h or re.search(r'ds\d+', h):
        return 'Synology NAS'
    
    # Cameras
    if any(x in h for x in ['camera', 'ipc', 'ipcam', 'cam-', 'nvr', 'dvr']):
        return 'IP Camera/NVR'
    
    # Smart Home
    if any(x in h for x in ['hue-', 'philips-hue', 'homekit']):
        return 'Smart Light'
    if 'nest-' in h or 'google-home' in h:
        return 'Google Home/Nest'
    if 'alexa' in h or 'echo-' in h:
        return 'Amazon Echo'
    
    # Networking
    if any(x in h for x in ['switch', 'router', 'gateway']):
        return 'Network Device'
    if h.startswith('ap-') or 'access-point' in h or h.startswith('wap'):
        return 'WiFi Access Point'
    if 'ubiquiti' in h or 'unifi' in h:
        return 'Ubiquiti Network Device'
    
    # Computers
    if h.startswith('desktop-') and len(h) > 15:
        return 'Windows Desktop'
    if h.endswith('.local') and '-' not in h:
        return 'macOS/Linux'
    
    # Game Consoles
    if any(x in h for x in ['playstation', 'ps4', 'ps5', 'xbox']):
        return 'Game Console'
    if 'nintendo' in h or 'switch' in h:
        return 'Nintendo'
    
    # Smart TV
    if any(x in h for x in ['tv-', 'smarttv', 'roku', 'firetv']):
        return 'Smart TV'
    
    return None


def guess_device_type_from_ports(open_ports: List[int]) -> Optional[str]:
    """Infer device type from open port combinations"""
    if not open_ports:
        return None
    
    ports = set(open_ports)
    
    # Printers (high confidence)
    if {631, 9100} <= ports:
        return 'Network Printer'
    if 9100 in ports:
        return 'Printer (JetDirect)'
    if 515 in ports:
        return 'Printer (LPD)'
    
    # NAS/File Servers
    if {139, 445} <= ports:  # SMB
        if any(p in ports for p in [5000, 5001, 5005, 5006]):  # Synology
            return 'Synology NAS'
        if 548 in ports:  # AFP
            return 'NAS (AFP)'
        if 2049 in ports:  # NFS
            return 'NAS/File Server'
        if {80, 443} <= ports:
            return 'NAS/Windows Server'
    
    # IP Cameras
    if 554 in ports:  # RTSP
        if any(p in ports for p in [8000, 8080, 80]):
            return 'IP Camera'
    if {80, 8000} <= ports and 37777 in ports:  # Dahua
        return 'IP Camera (Dahua)'
    
    # Web Servers
    if 80 in ports or 443 in ports:
        if 3000 in ports:
            return 'Web Server (Node.js)'
        if 8080 in ports:
            return 'Web Server/IoT'
        if 8443 in ports:
            return 'Web Server (Alt HTTPS)'
    
    # Database Servers
    if 3306 in ports:
        return 'MySQL Server'
    if 5432 in ports:
        return 'PostgreSQL Server'
    if 27017 in ports:
        return 'MongoDB Server'
    if 6379 in ports:
        return 'Redis Server'
    
    # Network Equipment
    if {22, 80, 443} <= ports and 161 in ports:  # SSH+HTTP+SNMP
        return 'Network Switch/Router'
    if 161 in ports and 162 in ports:  # SNMP
        return 'Managed Network Device'
    
    # Windows
    if {135, 139, 445} <= ports:
        if 3389 in ports:  # RDP
            return 'Windows Desktop/Server'
        return 'Windows Machine'
    
    # Remote Access
    if 3389 in ports:
        return 'Windows RDP'
    if 5900 in ports:
        return 'VNC Server'
    
    # VoIP
    if 5060 in ports or 5061 in ports:
        return 'VoIP Device'
    
    return None


def guess_device_type_from_mdns(services: List[str]) -> Optional[str]:
    """Infer device type from mDNS service combinations"""
    if not services:
        return None
    
    svc = set(s.lower() for s in services)
    
    # Apple devices
    if '_airplay._tcp' in svc:
        if '_raop._tcp' in svc:
            if '_ssh._tcp' in svc:
                return 'macOS'
            return 'Apple TV/HomePod'
        if '_homekit._tcp' in svc:
            return 'HomeKit Device'
        return 'AirPlay Device'
    
    # HomeKit
    if '_hap._tcp' in svc:
        return 'HomeKit Accessory'
    
    # Chromecast
    if '_googlecast._tcp' in svc:
        return 'Chromecast/Google Home'
    
    # Printers
    if '_ipp._tcp' in svc or '_printer._tcp' in svc:
        if '_scanner._tcp' in svc:
            return 'Printer/Scanner (MFP)'
        return 'Network Printer'
    
    # File Sharing
    if '_smb._tcp' in svc:
        if '_afpovertcp._tcp' in svc:
            return 'macOS/NAS (AFP+SMB)'
        return 'SMB File Server'
    if '_nfs._tcp' in svc:
        return 'NFS Server'
    
    # Web Services
    if '_http._tcp' in svc or '_https._tcp' in svc:
        if '_workstation._tcp' in svc:
            return 'Computer'
        if '_device-info._tcp' in svc:
            return 'Network Device'
    
    # Smart Home
    if '_hue._tcp' in svc:
        return 'Philips Hue Bridge'
    if '_spotify-connect._tcp' in svc:
        return 'Spotify Connect Device'
    if '_sonos._tcp' in svc:
        return 'Sonos Speaker'
    
    # IoT
    if '_mqtt._tcp' in svc:
        return 'MQTT Device/Broker'
    if '_esphomelib._tcp' in svc:
        return 'ESPHome Device'
    
    return None


def extract_os_from_banner(port: int, banner: str) -> Dict[str, str]:
    """
    Extract OS name and version from TCP banner.
    Returns: {'os': 'OS Name', 'os_version': 'Version'}
    """
    if not banner:
        return {}
    
    result = {}
    b = banner.lower()
    original_banner = banner
    
    # SSH banners - very detailed
    if port == 22 and 'ssh' in b:
        # OpenSSH format: SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.1
        match = re.search(r'openssh[_\s]+([\d.]+p?\d*)', b, re.IGNORECASE)
        if match:
            ssh_version = match.group(1)
            
            # Try to extract OS and version
            if 'ubuntu' in b:
                # Extract Ubuntu version
                ubuntu_match = re.search(r'ubuntu[- ]([\d.]+)', b, re.IGNORECASE)
                if ubuntu_match:
                    result['os'] = 'Ubuntu Linux'
                    result['os_version'] = ubuntu_match.group(1)
                else:
                    result['os'] = 'Ubuntu Linux'
            elif 'debian' in b:
                # Extract Debian version
                debian_match = re.search(r'debian[- ]([\d.]+)', b, re.IGNORECASE)
                if debian_match:
                    result['os'] = 'Debian Linux'
                    result['os_version'] = debian_match.group(1)
                else:
                    result['os'] = 'Debian Linux'
            elif 'raspbian' in b:
                result['os'] = 'Raspbian'
            elif 'centos' in b:
                result['os'] = 'CentOS Linux'
            elif 'redhat' in b or 'rhel' in b:
                result['os'] = 'Red Hat Linux'
            elif 'fedora' in b:
                result['os'] = 'Fedora Linux'
            elif 'freebsd' in b:
                match = re.search(r'freebsd[- ]?([\d.]+)?', b, re.IGNORECASE)
                result['os'] = 'FreeBSD'
                if match and match.group(1):
                    result['os_version'] = match.group(1)
        elif 'dropbear' in b:
            result['os'] = 'Embedded Linux'

def guess_device_from_banner(port: int, banner: str) -> Dict[str, str]:
    """Extract device info from TCP banner (legacy wrapper)"""
    if not banner:
        return {}
    
    result = extract_os_from_banner(port, banner)
    b = banner.lower()
    
    # HTTP Server headers
    if port in [80, 443, 8080]:
        if 'apache' in b:
            result['software'] = 'Apache'
            if 'ubuntu' in b:
                result['os'] = 'Ubuntu'
            elif 'debian' in b:
                result['os'] = 'Debian'
        elif 'nginx' in b:
            result['software'] = 'Nginx'
        elif 'iis' in b:
            result['software'] = 'IIS'
            result['os'] = 'Windows'
        elif 'synology' in b:
            result['device_type'] = 'Synology NAS'
        elif 'qnap' in b:
            result['device_type'] = 'QNAP NAS'
    
    # FTP banners
    if port == 21:
        if 'synology' in b:
            result['device_type'] = 'Synology NAS'
        elif 'vsftpd' in b:
            result['software'] = 'vsftpd'
    
    # Telnet/Console
    if port == 23:
        if 'dd-wrt' in b:
            result['device_type'] = 'DD-WRT Router'
        elif 'openwrt' in b:
            result['device_type'] = 'OpenWrt Router'
    
    return result


def merge_device_identifications(device: Dict) -> Dict:
    """
    Merge all identification sources and pick best values
    Priority: User override > Pattern match > Discovered > OUI
    """
    # Device type priority
    if not device.get('device_type'):
        # Try patterns in order
        device_type = (
            guess_device_type_from_mdns(device.get('mdns_services', [])) or
            guess_device_type_from_hostname(device.get('hostname', '')) or
            guess_device_type_from_ports(device.get('open_ports', []))
        )
        if device_type:
            device['device_type'] = device_type
            device['device_type_source'] = 'pattern_match'
    
    # Manufacturer: prefer discovered manufacturer over OUI vendor
    if not device.get('manufacturer') and device.get('vendor'):
        device['manufacturer'] = device['vendor']
    
    return device


def get_device_category(device_type: str) -> str:
    """Categorize device types into broad categories for filtering"""
    if not device_type:
        return 'Unknown'
    
    dt = device_type.lower()
    
    if any(x in dt for x in ['phone', 'iphone', 'android', 'mobile']):
        return 'Mobile'
    if any(x in dt for x in ['printer', 'mfp']):
        return 'Printer'
    if any(x in dt for x in ['nas', 'storage', 'diskstation']):
        return 'Storage'
    if any(x in dt for x in ['camera', 'nvr', 'dvr']):
        return 'Camera'
    if any(x in dt for x in ['switch', 'router', 'gateway', 'access point', 'ap']):
        return 'Network'
    if any(x in dt for x in ['iot', 'esp', 'tasmota', 'shelly', 'smart']):
        return 'IoT'
    if any(x in dt for x in ['computer', 'desktop', 'laptop', 'workstation', 'server']):
        return 'Computer'
    if any(x in dt for x in ['tv', 'chromecast', 'roku']):
        return 'Media'
    
    return 'Other'

