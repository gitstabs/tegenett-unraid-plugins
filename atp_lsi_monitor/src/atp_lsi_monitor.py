#!/usr/bin/env python3
"""
ATP LSI Monitor - Python Daemon
v2026.01.31

Monitors LSI SAS HBA cards (SAS2308, 9207-8i, etc.) for:
- IOC Temperature
- PHY Link Errors
- Firmware/Hardware Info
- Connected Devices

Features:
- HTTP API server
- SQLite database for history
- Discord/Notifiarr/Gotify notifications
- Scheduled monitoring and reports
- Configurable alerting thresholds
"""

import os
import sys
import json
import logging
import sqlite3
import threading
import signal
import subprocess
import re
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError
import hashlib

# ============================================
# CONFIGURATION
# ============================================

PLUGIN_NAME = "atp_lsi_monitor"
DEFAULT_PORT = 39800
VERSION = "2026.01.31l"

# Paths
DATA_DIR = f"/mnt/user/appdata/{PLUGIN_NAME}"
CONFIG_DIR = f"/boot/config/plugins/{PLUGIN_NAME}"
SETTINGS_FILE = f"{CONFIG_DIR}/settings.json"
DB_FILE = f"{DATA_DIR}/lsi_monitor.db"
LOG_FILE = f"{DATA_DIR}/logs/{PLUGIN_NAME}.log"
PID_FILE = f"/var/run/{PLUGIN_NAME}.pid"

# Default lsiutil path - plugin will bundle it
LSIUTIL_BUNDLED = f"/usr/local/emhttp/plugins/{PLUGIN_NAME}/lsiutil"
LSIUTIL_DEFAULT = LSIUTIL_BUNDLED

# Default settings
DEFAULT_SETTINGS = {
    # General
    "ENABLED": True,
    "SERVER_PORT": DEFAULT_PORT,
    "LOG_LEVEL": "INFO",

    # LSI Configuration
    "LSIUTIL_PATH": LSIUTIL_DEFAULT,
    "LSI_PORT": 1,  # lsiutil port number (usually 1)
    "POLL_INTERVAL": 300,  # 5 minutes default

    # Temperature Thresholds
    "TEMP_WARNING": 50,  # Yellow warning
    "TEMP_CRITICAL": 65,  # Red critical
    "TEMP_SHUTDOWN_ENABLED": False,  # Auto-shutdown on critical

    # Alerting
    "ALERT_ON_WARNING": True,
    "ALERT_ON_CRITICAL": True,
    "ALERT_ON_PHY_ERRORS": True,
    "ALERT_COOLDOWN": 3600,  # Don't repeat same alert for 1 hour

    # Notification Services
    "NOTIFICATION_SERVICE": "none",  # none, discord, notifiarr, gotify, ntfy, pushover

    # Discord
    "DISCORD_WEBHOOK": "",

    # Notifiarr
    "NOTIFIARR_API_KEY": "",
    "NOTIFIARR_CHANNEL": "",

    # Gotify
    "GOTIFY_URL": "",
    "GOTIFY_TOKEN": "",

    # ntfy
    "NTFY_URL": "https://ntfy.sh",
    "NTFY_TOPIC": "",

    # Pushover
    "PUSHOVER_USER_KEY": "",
    "PUSHOVER_API_TOKEN": "",

    # Scheduled Reports
    "DAILY_REPORT_ENABLED": False,
    "DAILY_REPORT_HOUR": 8,
    "WEEKLY_REPORT_ENABLED": False,
    "WEEKLY_REPORT_DAY": 0,  # 0=Monday
    "WEEKLY_REPORT_HOUR": 9,
    "MONTHLY_REPORT_ENABLED": False,
    "MONTHLY_REPORT_DAY": 1,
    "MONTHLY_REPORT_HOUR": 10,
}

# ============================================
# GLOBALS
# ============================================

settings = {}
db_lock = threading.Lock()
shutdown_event = threading.Event()
last_alerts = {}  # Track last alert times to prevent spam
monitor_thread = None
scheduler_thread = None

# ============================================
# LOGGING
# ============================================

def setup_logging():
    """Configure logging to file only (no console to avoid duplicates from systemd)."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    level = getattr(logging, settings.get("LOG_LEVEL", "INFO"))

    # Get the root logger
    logger = logging.getLogger()

    # Only setup if not already configured
    if logger.handlers:
        return

    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler only - console causes duplicates when run as service
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ============================================
# SETTINGS
# ============================================

def load_settings():
    """Load settings from JSON file."""
    global settings
    settings = DEFAULT_SETTINGS.copy()

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    return settings

def save_settings(new_settings):
    """Save settings to JSON file."""
    global settings

    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Update settings
    for key, value in new_settings.items():
        if key in DEFAULT_SETTINGS:
            # Type conversion
            if isinstance(DEFAULT_SETTINGS[key], bool):
                settings[key] = value if isinstance(value, bool) else str(value).lower() == 'true'
            elif isinstance(DEFAULT_SETTINGS[key], int):
                settings[key] = int(value) if value not in [None, ''] else DEFAULT_SETTINGS[key]
            else:
                settings[key] = value

    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

    logging.info("Settings saved")
    return settings

# ============================================
# DATABASE
# ============================================

def get_db():
    """Get database connection."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database schema."""
    with db_lock:
        conn = get_db()
        cursor = conn.cursor()

        # Schema version tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row[0] else 0

        # Migration v1: Initial schema
        if current_version < 1:
            logging.info("Running migration v1: Initial schema")

            # Temperature history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temperature_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    ioc_temp INTEGER,
                    board_temp INTEGER
                )
            """)

            # PHY error history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS phy_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    phy_number INTEGER,
                    invalid_dword INTEGER DEFAULT 0,
                    running_disparity INTEGER DEFAULT 0,
                    loss_of_sync INTEGER DEFAULT 0,
                    phy_reset_problem INTEGER DEFAULT 0
                )
            """)

            # Hardware info cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hardware_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    firmware_version TEXT,
                    bios_version TEXT,
                    chip_name TEXT,
                    chip_revision TEXT,
                    board_name TEXT,
                    board_tracer TEXT,
                    raw_output TEXT
                )
            """)

            # Alert history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    notified INTEGER DEFAULT 0
                )
            """)

            # Connected devices
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
                    sas_address TEXT UNIQUE,
                    device_name TEXT,
                    phy_number INTEGER,
                    link_rate TEXT,
                    device_type TEXT
                )
            """)

            cursor.execute("INSERT INTO schema_version (version) VALUES (1)")

        conn.commit()
        conn.close()
        logging.info(f"Database initialized (schema v{max(current_version, 1)})")

# ============================================
# LSIUTIL INTERFACE
# ============================================

def run_lsiutil(args, timeout=30):
    """
    Run lsiutil command and return output.

    Args:
        args: List of arguments to pass to lsiutil
        timeout: Command timeout in seconds

    Returns:
        tuple: (success, output_string)
    """
    lsiutil_path = settings.get("LSIUTIL_PATH", LSIUTIL_DEFAULT)

    if not os.path.exists(lsiutil_path):
        return False, f"lsiutil not found at {lsiutil_path}"

    # Ensure executable
    try:
        os.chmod(lsiutil_path, 0o755)
    except Exception:
        pass

    cmd = [lsiutil_path] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return True, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)

def get_temperature():
    """
    Read IOC temperature from LSI HBA.

    Returns:
        dict: {success, ioc_temp, board_temp, unit}
    """
    port = settings.get("LSI_PORT", 1)

    # Command: lsiutil -p1 -a 25,2,0,0
    # This reads IOC temperature via diagnostic page
    success, output = run_lsiutil([f"-p{port}", "-a", "25,2,0,0"])

    if not success:
        return {"success": False, "error": output}

    # Parse IOCTemperature: 0xXX from output
    match = re.search(r'IOCTemperature:\s*0x([0-9A-Fa-f]+)', output)

    if match:
        hex_temp = match.group(1)
        try:
            temp_celsius = int(hex_temp, 16)
            return {
                "success": True,
                "ioc_temp": temp_celsius,
                "board_temp": None,  # Not all cards report this
                "unit": "C",
                "raw": output
            }
        except ValueError:
            return {"success": False, "error": f"Invalid temperature value: {hex_temp}"}

    return {"success": False, "error": "Could not parse temperature from output", "raw": output}

def get_firmware_info():
    """
    Get firmware and hardware info from LSI HBA.

    Returns:
        dict: Firmware/hardware details
    """
    port = settings.get("LSI_PORT", 1)

    # Option 1: Identify firmware
    success, output = run_lsiutil([f"-p{port}", "-a", "1"])

    if not success:
        return {"success": False, "error": output}

    info = {
        "success": True,
        "firmware_version": None,
        "bios_version": None,
        "chip_name": None,
        "chip_revision": None,
        "board_name": None,
        "it_mode": False,
        "raw": output
    }

    # Parse firmware version from "Firmware image's version is MPTFW-20.00.07.00-IT"
    fw_image_match = re.search(r"Firmware\s+image's\s+version\s+is\s+\S*?(\d+\.\d+\.\d+\.\d+)", output, re.IGNORECASE)
    if fw_image_match:
        info["firmware_version"] = fw_image_match.group(1)
    else:
        # Fallback: "firmware version is 14000700 (20.00.07)"
        fw_match = re.search(r'firmware\s+version\s+is\s+[0-9A-Fa-f]+\s*\(([0-9.]+)\)', output, re.IGNORECASE)
        if fw_match:
            info["firmware_version"] = fw_match.group(1)
        else:
            # Last fallback: raw hex
            fw_hex_match = re.search(r'Firmware\s*(?:Rev|Version)?\s*[:\s]+([0-9A-Fa-f]{8})', output, re.IGNORECASE)
            if fw_hex_match:
                fw_raw = fw_hex_match.group(1)
                try:
                    fw_int = int(fw_raw, 16)
                    major = (fw_int >> 24) & 0xFF
                    minor = (fw_int >> 16) & 0xFF
                    patch = (fw_int >> 8) & 0xFF
                    build = fw_int & 0xFF
                    info["firmware_version"] = f"{major}.{minor:02d}.{patch:02d}.{build:02d}"
                except ValueError:
                    info["firmware_version"] = fw_raw

    # Parse BIOS version from "x86 BIOS image's version is MPT2BIOS-7.39.02.00"
    bios_match = re.search(r"BIOS\s+image's\s+version\s+is\s+\S*?(\d+\.\d+\.\d+\.\d+)", output, re.IGNORECASE)
    if bios_match:
        info["bios_version"] = bios_match.group(1)
    else:
        # Fallback pattern
        bios_match = re.search(r'BIOS\s*(?:Version)?\s*[:\s]+(\d+\.\d+[\d.]*)', output, re.IGNORECASE)
        if bios_match:
            info["bios_version"] = bios_match.group(1)

    # Parse chip name - look for "LSI Logic SAS2308" pattern
    chip_match = re.search(r'LSI\s*Logic\s*(SAS\d+)', output, re.IGNORECASE)
    if not chip_match:
        # Also try to find standalone SAS#### pattern
        chip_match = re.search(r'\b(SAS\d{4})\b', output)
    if chip_match:
        info["chip_name"] = chip_match.group(1)

    # Parse board name/assembly - look for "LSI Logic" and "Not Packaged Yet"
    board_match = re.search(r'(?:Board|Assembly)\s*(?:Name)?\s*[:\s]*(.*?)(?:\n|$)', output, re.IGNORECASE)
    if board_match and board_match.group(1).strip():
        info["board_name"] = board_match.group(1).strip()
    else:
        # Try to extract from LSI Logic line
        lsi_match = re.search(r'^\s*(LSI Logic)\s*$', output, re.MULTILINE)
        if lsi_match:
            info["board_name"] = "LSI Logic"

    # Check for IT Mode - look for "-IT" in firmware string
    if re.search(r'-IT\b', output) or re.search(r'IT\s*(?:mode|firmware)', output, re.IGNORECASE):
        info["it_mode"] = True

    return info

def get_phy_errors():
    """
    Get PHY link error statistics.

    Returns:
        dict: PHY error counts per PHY
    """
    port = settings.get("LSI_PORT", 1)

    # Option 20, 12: Diagnostics -> Phy/Link Test
    success, output = run_lsiutil([f"-p{port}", "-a", "20,12,0"])

    if not success:
        return {"success": False, "error": output}

    phys = []

    # Parse each PHY's error counts
    # Pattern: Adapter Phy N: Link Up/Down
    #          Invalid DWord Count XXX
    #          Running Disparity Error Count XXX
    #          Loss of DWord Synch Count XXX
    #          Phy Reset Problem Count XXX

    phy_blocks = re.split(r'Adapter Phy\s+(\d+)', output)

    for i in range(1, len(phy_blocks), 2):
        if i + 1 < len(phy_blocks):
            phy_num = int(phy_blocks[i])
            phy_data = phy_blocks[i + 1]

            phy_info = {
                "phy_number": phy_num,
                "link_up": "Link Up" in phy_data,
                "invalid_dword": 0,
                "running_disparity": 0,
                "loss_of_sync": 0,
                "phy_reset_problem": 0
            }

            # Parse error counts
            invalid_match = re.search(r'Invalid DWord Count\s+(\d+)', phy_data)
            if invalid_match:
                phy_info["invalid_dword"] = int(invalid_match.group(1))

            disparity_match = re.search(r'Running Disparity Error Count\s+(\d+)', phy_data)
            if disparity_match:
                phy_info["running_disparity"] = int(disparity_match.group(1))

            sync_match = re.search(r'Loss of DWord Synch Count\s+(\d+)', phy_data)
            if sync_match:
                phy_info["loss_of_sync"] = int(sync_match.group(1))

            reset_match = re.search(r'Phy Reset Problem Count\s+(\d+)', phy_data)
            if reset_match:
                phy_info["phy_reset_problem"] = int(reset_match.group(1))

            phys.append(phy_info)

    return {
        "success": True,
        "phys": phys,
        "raw": output
    }

def get_connected_devices():
    """
    Get list of connected devices/drives.

    Returns:
        dict: List of connected devices
    """
    port = settings.get("LSI_PORT", 1)

    # Option 16: Display attached devices
    success, output = run_lsiutil([f"-p{port}", "-a", "16"])

    if not success:
        return {"success": False, "error": output}

    devices = []
    sata_targets = []
    sas_initiators = []

    # Parse the device table format:
    # B___T     SASAddress     PhyNum  Handle  Parent  Type
    # 0   1  4433221101000000     1     0009    0001   SATA Target
    # or without B___T for initiators:
    #        500605b006c9f310           0001           SAS Initiator

    lines = output.split('\n')
    for line in lines:
        # Match SATA Target lines: " 0   1  4433221101000000     1     0009    0001   SATA Target"
        sata_match = re.match(
            r'\s*(\d+)\s+(\d+)\s+([0-9A-Fa-f]{16})\s+(\d+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+SATA\s+Target',
            line, re.IGNORECASE
        )
        if sata_match:
            bus, target, sas_addr, phy_num, handle, parent = sata_match.groups()
            sata_targets.append({
                "sas_address": sas_addr.upper(),
                "device_name": f"Bus {bus}, Target {target}",
                "device_type": "SATA Target",
                "phy_num": int(phy_num),
                "handle": handle.upper()
            })
            continue

        # Match SAS Initiator lines: "        500605b006c9f310           0001           SAS Initiator"
        sas_match = re.match(
            r'\s+([0-9A-Fa-f]{16})\s+([0-9A-Fa-f]+)\s+SAS\s+Initiator',
            line, re.IGNORECASE
        )
        if sas_match:
            sas_addr, handle = sas_match.groups()
            sas_initiators.append({
                "sas_address": sas_addr.upper(),
                "device_name": "SAS Initiator",
                "device_type": "SAS Initiator",
                "handle": handle.upper()
            })

    # Parse link speeds from: "SAS2308's links are down, 6.0 G, 6.0 G, 6.0 G, down, down, down, down"
    link_speeds = []
    link_match = re.search(r"links are\s+(.*?)(?:\n|$)", output, re.IGNORECASE)
    if link_match:
        speeds_str = link_match.group(1)
        # Parse comma-separated speeds
        for speed in speeds_str.split(','):
            speed = speed.strip()
            if 'down' in speed.lower():
                link_speeds.append(None)
            else:
                link_speeds.append(speed)

    # Add link speeds to SATA targets based on PHY number
    for device in sata_targets:
        phy = device.get('phy_num', 0)
        if phy > 0 and phy <= len(link_speeds):
            device['link_speed'] = link_speeds[phy - 1]

    # Combine devices - SATA targets are the actual drives
    devices = sata_targets

    return {
        "success": True,
        "devices": devices,
        "device_count": len(sata_targets),
        "sata_targets": len(sata_targets),
        "sas_initiators": len(sas_initiators),
        "link_speeds": link_speeds,
        "raw": output
    }

# ============================================
# MONITORING
# ============================================

def record_temperature():
    """Record current temperature to database."""
    temp_data = get_temperature()

    if not temp_data.get("success"):
        logging.warning(f"Failed to read temperature: {temp_data.get('error')}")
        return None

    ioc_temp = temp_data.get("ioc_temp")
    board_temp = temp_data.get("board_temp")

    with db_lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO temperature_history (ioc_temp, board_temp) VALUES (?, ?)",
            (ioc_temp, board_temp)
        )
        conn.commit()
        conn.close()

    logging.debug(f"Recorded temperature: {ioc_temp}°C")

    # Check thresholds and alert if needed
    check_temperature_alerts(ioc_temp)

    return ioc_temp

def check_temperature_alerts(temp):
    """Check temperature against thresholds and send alerts."""
    if temp is None:
        return

    warning_threshold = settings.get("TEMP_WARNING", 50)
    critical_threshold = settings.get("TEMP_CRITICAL", 65)

    severity = None
    message = None

    if temp >= critical_threshold:
        severity = "critical"
        message = f"LSI HBA temperature is CRITICAL: {temp}°C (threshold: {critical_threshold}°C)"

        # Optional: Trigger shutdown
        if settings.get("TEMP_SHUTDOWN_ENABLED"):
            logging.critical("Temperature shutdown triggered!")
            # Could call unraid shutdown here

    elif temp >= warning_threshold:
        severity = "warning"
        message = f"LSI HBA temperature is HIGH: {temp}°C (threshold: {warning_threshold}°C)"

    if severity and should_alert("temperature", severity):
        log_alert("temperature", severity, message)

        if (severity == "warning" and settings.get("ALERT_ON_WARNING")) or \
           (severity == "critical" and settings.get("ALERT_ON_CRITICAL")):
            send_notification(f"LSI HBA {severity.upper()}", message, severity)

def record_phy_errors():
    """Record PHY errors to database and check for issues."""
    phy_data = get_phy_errors()

    if not phy_data.get("success"):
        logging.warning(f"Failed to read PHY errors: {phy_data.get('error')}")
        return

    with db_lock:
        conn = get_db()
        cursor = conn.cursor()

        for phy in phy_data.get("phys", []):
            cursor.execute("""
                INSERT INTO phy_errors
                (phy_number, invalid_dword, running_disparity, loss_of_sync, phy_reset_problem)
                VALUES (?, ?, ?, ?, ?)
            """, (
                phy["phy_number"],
                phy["invalid_dword"],
                phy["running_disparity"],
                phy["loss_of_sync"],
                phy["phy_reset_problem"]
            ))

            # Check for significant error increases
            total_errors = (
                phy["invalid_dword"] +
                phy["running_disparity"] +
                phy["loss_of_sync"] +
                phy["phy_reset_problem"]
            )

            if total_errors > 1000 and settings.get("ALERT_ON_PHY_ERRORS"):
                if should_alert(f"phy_{phy['phy_number']}", "warning"):
                    message = f"PHY {phy['phy_number']} has accumulated {total_errors} errors"
                    log_alert("phy_errors", "warning", message)
                    send_notification("LSI PHY Errors", message, "warning")

        conn.commit()
        conn.close()

def should_alert(alert_key, severity):
    """Check if we should send an alert (cooldown check)."""
    cooldown = settings.get("ALERT_COOLDOWN", 3600)
    now = time.time()

    key = f"{alert_key}_{severity}"
    last_time = last_alerts.get(key, 0)

    if now - last_time >= cooldown:
        last_alerts[key] = now
        return True

    return False

def log_alert(alert_type, severity, message):
    """Log alert to database."""
    with db_lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO alerts (alert_type, severity, message) VALUES (?, ?, ?)",
            (alert_type, severity, message)
        )
        conn.commit()
        conn.close()

    if severity == "critical":
        logging.critical(message)
    elif severity == "warning":
        logging.warning(message)
    else:
        logging.info(message)

# ============================================
# NOTIFICATIONS
# ============================================

def send_notification(title, message, severity="info"):
    """Send notification via configured service."""
    service = settings.get("NOTIFICATION_SERVICE", "none")

    if service == "none":
        return

    try:
        if service == "discord":
            send_discord_notification(title, message, severity)
        elif service == "notifiarr":
            send_notifiarr_notification(title, message, severity)
        elif service == "gotify":
            send_gotify_notification(title, message, severity)
        elif service == "ntfy":
            send_ntfy_notification(title, message, severity)
        elif service == "pushover":
            send_pushover_notification(title, message, severity)
    except Exception as e:
        logging.error(f"Failed to send {service} notification: {e}")

def get_severity_color(severity):
    """Get color code for severity level."""
    colors = {
        "critical": 0xcc0000,  # Red
        "warning": 0xffaa00,   # Orange
        "info": 0x00cc66,      # Green
        "success": 0x00cc66    # Green
    }
    return colors.get(severity, 0x3498db)

def send_discord_notification(title, message, severity):
    """Send Discord webhook notification."""
    webhook_url = settings.get("DISCORD_WEBHOOK", "").strip()
    if not webhook_url:
        logging.warning("Discord webhook not configured")
        return

    # Validate webhook URL format
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        logging.error(f"Invalid Discord webhook URL format. Must start with https://discord.com/api/webhooks/")
        return

    logging.debug(f"Sending Discord notification to webhook: {webhook_url[:60]}...")

    color = get_severity_color(severity)
    hostname = os.uname().nodename if hasattr(os, 'uname') else "Unknown"

    payload = {
        "embeds": [{
            "title": f"🌡️ {title}",
            "description": message,
            "color": color,
            "fields": [
                {"name": "Host", "value": hostname, "inline": True},
                {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
            ],
            "footer": {"text": "ATP LSI Monitor"}
        }]
    }

    try:
        req = Request(webhook_url, data=json.dumps(payload).encode())
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'ATP-LSI-Monitor/1.0')
        response = urlopen(req, timeout=10)
        logging.info(f"Discord notification sent: {title}")
    except URLError as e:
        # Log more details about the error
        if hasattr(e, 'code'):
            logging.error(f"Discord webhook returned HTTP {e.code}: {e.reason}")
            if e.code == 403:
                logging.error("403 Forbidden - Check that the webhook URL is correct and not expired")
        else:
            logging.error(f"Discord webhook connection error: {e.reason}")
        raise

def send_notifiarr_notification(title, message, severity):
    """Send Notifiarr notification."""
    api_key = settings.get("NOTIFIARR_API_KEY")
    channel = settings.get("NOTIFIARR_CHANNEL")

    if not api_key:
        logging.warning("Notifiarr API key not configured")
        return

    url = f"https://notifiarr.com/api/v1/notification/passthrough/{api_key}"
    color = format(get_severity_color(severity), 'x')

    payload = {
        "notification": {
            "update": False,
            "name": "LSI HBA Monitor",
            "event": f"LSI_{severity.upper()}"
        },
        "discord": {
            "color": color,
            "text": {
                "title": title,
                "description": message,
                "footer": "ATP LSI Monitor"
            },
            "ids": {
                "channel": channel
            } if channel else {}
        }
    }

    req = Request(url, data=json.dumps(payload).encode())
    req.add_header('Content-Type', 'application/json')
    urlopen(req, timeout=10)
    logging.info(f"Notifiarr notification sent: {title}")

def send_gotify_notification(title, message, severity):
    """Send Gotify notification."""
    gotify_url = settings.get("GOTIFY_URL")
    token = settings.get("GOTIFY_TOKEN")

    if not gotify_url or not token:
        logging.warning("Gotify not configured")
        return

    priority_map = {"critical": 10, "warning": 7, "info": 4}
    priority = priority_map.get(severity, 4)

    url = f"{gotify_url.rstrip('/')}/message?token={token}"
    payload = {
        "title": title,
        "message": message,
        "priority": priority
    }

    req = Request(url, data=json.dumps(payload).encode())
    req.add_header('Content-Type', 'application/json')
    urlopen(req, timeout=10)
    logging.info(f"Gotify notification sent: {title}")

def send_ntfy_notification(title, message, severity):
    """Send ntfy notification."""
    ntfy_url = settings.get("NTFY_URL", "https://ntfy.sh")
    topic = settings.get("NTFY_TOPIC")

    if not topic:
        logging.warning("ntfy topic not configured")
        return

    priority_map = {"critical": "urgent", "warning": "high", "info": "default"}
    priority = priority_map.get(severity, "default")

    url = f"{ntfy_url.rstrip('/')}/{topic}"

    req = Request(url, data=message.encode())
    req.add_header('Title', title)
    req.add_header('Priority', priority)
    req.add_header('Tags', 'thermometer' if 'temp' in title.lower() else 'warning')
    urlopen(req, timeout=10)
    logging.info(f"ntfy notification sent: {title}")

def send_pushover_notification(title, message, severity):
    """Send Pushover notification."""
    user_key = settings.get("PUSHOVER_USER_KEY")
    api_token = settings.get("PUSHOVER_API_TOKEN")

    if not user_key or not api_token:
        logging.warning("Pushover not configured")
        return

    priority_map = {"critical": 2, "warning": 1, "info": 0}
    priority = priority_map.get(severity, 0)

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": api_token,
        "user": user_key,
        "title": title,
        "message": message,
        "priority": priority
    }

    if priority == 2:
        payload["retry"] = 60
        payload["expire"] = 3600

    data = "&".join(f"{k}={v}" for k, v in payload.items()).encode()
    req = Request(url, data=data)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    urlopen(req, timeout=10)
    logging.info(f"Pushover notification sent: {title}")

# ============================================
# SCHEDULED REPORTS
# ============================================

def generate_daily_report():
    """Generate daily summary report."""
    with db_lock:
        conn = get_db()
        cursor = conn.cursor()

        # Get last 24 hours of temperature data
        cursor.execute("""
            SELECT
                MIN(ioc_temp) as min_temp,
                MAX(ioc_temp) as max_temp,
                AVG(ioc_temp) as avg_temp,
                COUNT(*) as readings
            FROM temperature_history
            WHERE timestamp > datetime('now', '-1 day')
        """)
        temp_stats = dict(cursor.fetchone())

        # Get alert count
        cursor.execute("""
            SELECT COUNT(*) as alert_count
            FROM alerts
            WHERE timestamp > datetime('now', '-1 day')
        """)
        alert_count = cursor.fetchone()[0]

        conn.close()

    if temp_stats['readings'] == 0:
        return None

    report = f"""📊 **Daily LSI HBA Report**

🌡️ **Temperature (24h)**
• Min: {temp_stats['min_temp']}°C
• Max: {temp_stats['max_temp']}°C
• Avg: {temp_stats['avg_temp']:.1f}°C
• Readings: {temp_stats['readings']}

⚠️ **Alerts**: {alert_count}
"""
    return report

def generate_weekly_report():
    """Generate weekly summary report."""
    with db_lock:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                MIN(ioc_temp) as min_temp,
                MAX(ioc_temp) as max_temp,
                AVG(ioc_temp) as avg_temp,
                COUNT(*) as readings
            FROM temperature_history
            WHERE timestamp > datetime('now', '-7 days')
        """)
        temp_stats = dict(cursor.fetchone())

        cursor.execute("""
            SELECT COUNT(*) as alert_count
            FROM alerts
            WHERE timestamp > datetime('now', '-7 days')
        """)
        alert_count = cursor.fetchone()[0]

        conn.close()

    if temp_stats['readings'] == 0:
        return None

    report = f"""📊 **Weekly LSI HBA Report**

🌡️ **Temperature (7 days)**
• Min: {temp_stats['min_temp']}°C
• Max: {temp_stats['max_temp']}°C
• Avg: {temp_stats['avg_temp']:.1f}°C
• Readings: {temp_stats['readings']}

⚠️ **Alerts**: {alert_count}
"""
    return report

def generate_monthly_report():
    """Generate monthly summary report."""
    with db_lock:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                MIN(ioc_temp) as min_temp,
                MAX(ioc_temp) as max_temp,
                AVG(ioc_temp) as avg_temp,
                COUNT(*) as readings
            FROM temperature_history
            WHERE timestamp > datetime('now', '-30 days')
        """)
        temp_stats = dict(cursor.fetchone())

        cursor.execute("""
            SELECT COUNT(*) as alert_count
            FROM alerts
            WHERE timestamp > datetime('now', '-30 days')
        """)
        alert_count = cursor.fetchone()[0]

        conn.close()

    if temp_stats['readings'] == 0:
        return None

    report = f"""📊 **Monthly LSI HBA Report**

🌡️ **Temperature (30 days)**
• Min: {temp_stats['min_temp']}°C
• Max: {temp_stats['max_temp']}°C
• Avg: {temp_stats['avg_temp']:.1f}°C
• Readings: {temp_stats['readings']}

⚠️ **Alerts**: {alert_count}
"""
    return report

# ============================================
# MONITORING THREADS
# ============================================

def monitor_loop():
    """Main monitoring loop - runs in background thread."""
    logging.info("Monitor loop started")

    while not shutdown_event.is_set():
        if settings.get("ENABLED", True):
            try:
                record_temperature()
                record_phy_errors()
            except Exception as e:
                logging.error(f"Monitor error: {e}")

        # Wait for next poll interval
        interval = settings.get("POLL_INTERVAL", 300)
        shutdown_event.wait(interval)

    logging.info("Monitor loop stopped")

def scheduler_loop():
    """Scheduler for daily/weekly/monthly reports."""
    logging.info("Scheduler started")

    last_daily = None
    last_weekly = None
    last_monthly = None

    while not shutdown_event.is_set():
        now = datetime.now()

        # Daily report
        if settings.get("DAILY_REPORT_ENABLED"):
            hour = settings.get("DAILY_REPORT_HOUR", 8)
            if now.hour == hour and last_daily != now.date():
                report = generate_daily_report()
                if report:
                    send_notification("Daily LSI Report", report, "info")
                last_daily = now.date()

        # Weekly report
        if settings.get("WEEKLY_REPORT_ENABLED"):
            day = settings.get("WEEKLY_REPORT_DAY", 0)
            hour = settings.get("WEEKLY_REPORT_HOUR", 9)
            if now.weekday() == day and now.hour == hour and last_weekly != now.date():
                report = generate_weekly_report()
                if report:
                    send_notification("Weekly LSI Report", report, "info")
                last_weekly = now.date()

        # Monthly report
        if settings.get("MONTHLY_REPORT_ENABLED"):
            day = settings.get("MONTHLY_REPORT_DAY", 1)
            hour = settings.get("MONTHLY_REPORT_HOUR", 10)
            if now.day == day and now.hour == hour and last_monthly != now.date():
                report = generate_monthly_report()
                if report:
                    send_notification("Monthly LSI Report", report, "info")
                last_monthly = now.date()

        # Check every minute
        shutdown_event.wait(60)

    logging.info("Scheduler stopped")

# ============================================
# API HANDLER
# ============================================

class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the API."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def get_post_data(self):
        """Parse POST body as JSON."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            # Status endpoint
            if path == '/api/status':
                temp = get_temperature()
                self.send_json({
                    'success': True,
                    'status': 'running',
                    'version': VERSION,
                    'enabled': settings.get('ENABLED', True),
                    'current_temp': temp.get('ioc_temp') if temp.get('success') else None
                })

            # Current temperature
            elif path == '/api/temperature':
                self.send_json(get_temperature())

            # Temperature history
            elif path == '/api/temperature/history':
                hours = int(query.get('hours', [24])[0])
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, ioc_temp, board_temp
                        FROM temperature_history
                        WHERE timestamp > datetime('now', ? || ' hours')
                        ORDER BY timestamp ASC
                    """, (f"-{hours}",))
                    history = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                self.send_json({'success': True, 'history': history})

            # Temperature stats
            elif path == '/api/temperature/stats':
                period = query.get('period', ['24h'])[0]
                period_map = {'24h': '-1 day', '7d': '-7 days', '30d': '-30 days'}
                sql_period = period_map.get(period, '-1 day')

                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        SELECT
                            MIN(ioc_temp) as min_temp,
                            MAX(ioc_temp) as max_temp,
                            AVG(ioc_temp) as avg_temp,
                            COUNT(*) as readings
                        FROM temperature_history
                        WHERE timestamp > datetime('now', '{sql_period}')
                    """)
                    stats = dict(cursor.fetchone())
                    conn.close()
                self.send_json({'success': True, **stats})

            # Firmware info
            elif path == '/api/firmware':
                self.send_json(get_firmware_info())

            # PHY errors
            elif path == '/api/phy':
                self.send_json(get_phy_errors())

            # Connected devices
            elif path == '/api/devices':
                self.send_json(get_connected_devices())

            # Alerts
            elif path == '/api/alerts':
                limit = int(query.get('limit', [50])[0])
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM alerts
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (limit,))
                    alerts = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                self.send_json({'success': True, 'alerts': alerts})

            # Health check (combined status)
            elif path == '/api/health':
                temp_data = get_temperature()
                phy_data = get_phy_errors()

                health = "healthy"
                issues = []

                if temp_data.get('success'):
                    temp = temp_data.get('ioc_temp', 0)
                    if temp >= settings.get('TEMP_CRITICAL', 65):
                        health = "critical"
                        issues.append(f"Temperature critical: {temp}°C")
                    elif temp >= settings.get('TEMP_WARNING', 50):
                        health = "warning"
                        issues.append(f"Temperature high: {temp}°C")
                else:
                    issues.append("Cannot read temperature")

                # Check PHY errors
                if phy_data.get('success'):
                    for phy in phy_data.get('phys', []):
                        total = sum([
                            phy.get('invalid_dword', 0),
                            phy.get('running_disparity', 0),
                            phy.get('loss_of_sync', 0),
                            phy.get('phy_reset_problem', 0)
                        ])
                        if total > 10000:
                            if health != "critical":
                                health = "warning"
                            issues.append(f"PHY {phy['phy_number']}: {total} errors")

                self.send_json({
                    'success': True,
                    'health': health,
                    'issues': issues,
                    'temperature': temp_data,
                    'phy': phy_data
                })

            # Settings
            elif path == '/api/settings':
                # Return settings without sensitive data
                safe_settings = settings.copy()
                for key in ['DISCORD_WEBHOOK', 'NOTIFIARR_API_KEY', 'GOTIFY_TOKEN',
                           'PUSHOVER_USER_KEY', 'PUSHOVER_API_TOKEN']:
                    if key in safe_settings and safe_settings[key]:
                        safe_settings[key] = '***configured***'
                self.send_json({'success': True, **safe_settings})

            # Logs
            elif path == '/api/logs':
                lines = int(query.get('lines', [200])[0])
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, 'r') as f:
                        log_lines = f.readlines()
                        logs = ''.join(log_lines[-lines:])
                else:
                    logs = 'No logs available'
                self.send_json({'success': True, 'logs': logs})

            else:
                self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        except Exception as e:
            logging.error(f"GET error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            data = self.get_post_data()

            # Save settings
            if path == '/api/settings':
                save_settings(data)
                self.send_json({'success': True, 'message': 'Settings saved'})

            # Manual temperature reading
            elif path == '/api/temperature/read':
                temp = record_temperature()
                self.send_json({'success': True, 'temperature': temp})

            # Test notification
            elif path == '/api/notification/test':
                try:
                    send_notification("Test Notification", "LSI Monitor notification test successful!", "info")
                    self.send_json({'success': True, 'message': 'Test notification sent'})
                except Exception as e:
                    self.send_json({'success': False, 'error': str(e)})

            # Generate report
            elif path == '/api/report':
                report_type = data.get('type', 'daily')
                if report_type == 'daily':
                    report = generate_daily_report()
                elif report_type == 'weekly':
                    report = generate_weekly_report()
                elif report_type == 'monthly':
                    report = generate_monthly_report()
                else:
                    report = None

                if report:
                    if data.get('send'):
                        send_notification(f"{report_type.title()} Report", report, "info")
                    self.send_json({'success': True, 'report': report})
                else:
                    self.send_json({'success': False, 'error': 'No data for report'})

            # Clear alerts
            elif path == '/api/alerts/clear':
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM alerts")
                    conn.commit()
                    conn.close()
                self.send_json({'success': True, 'message': 'Alerts cleared'})

            # Import legacy temperature data
            elif path == '/api/import':
                records = data.get('records', [])
                if not records:
                    self.send_json({'success': False, 'error': 'No records to import'})
                    return

                imported = 0
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    for record in records:
                        try:
                            timestamp = record.get('timestamp')
                            ioc_temp = record.get('ioc_temp')
                            if timestamp and ioc_temp is not None:
                                # Convert timestamp format if needed
                                cursor.execute(
                                    "INSERT OR IGNORE INTO temperature_history (timestamp, ioc_temp, board_temp) VALUES (?, ?, ?)",
                                    (timestamp, ioc_temp, None)
                                )
                                imported += 1
                        except Exception as e:
                            logging.warning(f"Failed to import record: {e}")
                    conn.commit()
                    conn.close()

                logging.info(f"Imported {imported} temperature records from legacy data")
                self.send_json({'success': True, 'imported': imported})

            else:
                self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        except Exception as e:
            logging.error(f"POST error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

# ============================================
# MAIN
# ============================================

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logging.info("Shutdown signal received")
    shutdown_event.set()

def write_pid():
    """Write PID file."""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid():
    """Remove PID file."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def main():
    """Main entry point."""
    global monitor_thread, scheduler_thread

    # Load settings first
    load_settings()

    # Setup logging
    setup_logging()

    logging.info(f"Starting {PLUGIN_NAME} daemon v{VERSION}...")

    # Initialize database
    init_database()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Write PID file
    write_pid()

    # Start monitor thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()

    # Start scheduler thread
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    # Start HTTP server
    port = settings.get('SERVER_PORT', DEFAULT_PORT)
    server = HTTPServer(('127.0.0.1', port), APIHandler)
    server.timeout = 1

    logging.info(f"API server listening on port {port}")

    try:
        while not shutdown_event.is_set():
            server.handle_request()
    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        server.server_close()
        remove_pid()
        logging.info("Daemon stopped")

if __name__ == '__main__':
    main()
