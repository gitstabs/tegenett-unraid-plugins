#!/usr/bin/env python3
"""
ATP Template - Python Daemon
v2026.01.31

A minimal template for ATP plugin daemons.
Replace 'template' with your plugin name throughout.

Features:
- HTTP API server (Flask-like, but lightweight)
- SQLite database
- Settings management
- Logging
"""

import os
import sys
import json
import logging
import sqlite3
import threading
import signal
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============================================
# CONFIGURATION
# ============================================

PLUGIN_NAME = "atp_template"
DEFAULT_PORT = 39999  # Change this to a unique port!

# Paths
DATA_DIR = f"/mnt/user/appdata/{PLUGIN_NAME}"
CONFIG_DIR = f"/boot/config/plugins/{PLUGIN_NAME}"
SETTINGS_FILE = f"{CONFIG_DIR}/settings.json"
DB_FILE = f"{DATA_DIR}/database.db"
LOG_FILE = f"{DATA_DIR}/logs/{PLUGIN_NAME}.log"
PID_FILE = f"/var/run/{PLUGIN_NAME}.pid"

# Default settings
DEFAULT_SETTINGS = {
    "SERVER_PORT": DEFAULT_PORT,
    "LOG_LEVEL": "INFO",
    "EXAMPLE_SETTING": "default_value",
}

# ============================================
# GLOBALS
# ============================================

settings = {}
db_lock = threading.Lock()
shutdown_event = threading.Event()

# ============================================
# LOGGING
# ============================================

def setup_logging():
    """Configure logging to file and console."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    level = getattr(logging, settings.get("LOG_LEVEL", "INFO"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

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

        # Create schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Get current version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row[0] else 0

        # Run migrations
        if current_version < 1:
            logging.info("Running migration v1: Initial schema")

            # Example table - replace with your actual schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("INSERT INTO schema_version (version) VALUES (1)")

        # Add more migrations as needed:
        # if current_version < 2:
        #     logging.info("Running migration v2: Add new column")
        #     cursor.execute("ALTER TABLE items ADD COLUMN new_field TEXT")
        #     cursor.execute("INSERT INTO schema_version (version) VALUES (2)")

        conn.commit()
        conn.close()

        logging.info(f"Database initialized (schema v{max(current_version, 1)})")

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
                self.send_json({
                    'success': True,
                    'status': 'running',
                    'version': '2026.01.31',
                    'uptime': 'TODO'
                })

            # Settings endpoint
            elif path == '/api/settings':
                self.send_json({'success': True, **settings})

            # Items endpoint (example)
            elif path == '/api/items':
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM items ORDER BY id DESC")
                    items = [dict(row) for row in cursor.fetchall()]
                    conn.close()
                self.send_json({'success': True, 'items': items})

            # Single item
            elif path.startswith('/api/items/'):
                item_id = int(path.split('/')[-1])
                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
                    row = cursor.fetchone()
                    conn.close()
                if row:
                    self.send_json({'success': True, 'item': dict(row)})
                else:
                    self.send_json({'success': False, 'error': 'Item not found'}, 404)

            # Logs endpoint
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

            # Create item
            elif path == '/api/items':
                name = data.get('name', '').strip()
                description = data.get('description', '')

                if not name:
                    self.send_json({'success': False, 'error': 'Name is required'}, 400)
                    return

                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO items (name, description) VALUES (?, ?)",
                        (name, description)
                    )
                    item_id = cursor.lastrowid
                    conn.commit()
                    conn.close()

                logging.info(f"Created item: {name} (id={item_id})")
                self.send_json({'success': True, 'id': item_id})

            else:
                self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        except Exception as e:
            logging.error(f"POST error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def do_PUT(self):
        """Handle PUT requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            data = self.get_post_data()

            # Update item
            if path.startswith('/api/items/'):
                item_id = int(path.split('/')[-1])

                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()

                    # Build update query dynamically
                    updates = []
                    values = []
                    for field in ['name', 'description', 'enabled']:
                        if field in data:
                            updates.append(f"{field} = ?")
                            values.append(data[field])

                    if updates:
                        updates.append("updated_at = CURRENT_TIMESTAMP")
                        values.append(item_id)

                        cursor.execute(
                            f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
                            values
                        )
                        conn.commit()

                    conn.close()

                logging.info(f"Updated item {item_id}")
                self.send_json({'success': True})

            else:
                self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        except Exception as e:
            logging.error(f"PUT error: {e}")
            self.send_json({'success': False, 'error': str(e)}, 500)

    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            # Delete item
            if path.startswith('/api/items/'):
                item_id = int(path.split('/')[-1])

                with db_lock:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
                    conn.commit()
                    conn.close()

                logging.info(f"Deleted item {item_id}")
                self.send_json({'success': True})

            else:
                self.send_json({'success': False, 'error': 'Unknown endpoint'}, 404)

        except Exception as e:
            logging.error(f"DELETE error: {e}")
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
    # Load settings first
    load_settings()

    # Setup logging
    setup_logging()

    logging.info(f"Starting {PLUGIN_NAME} daemon...")

    # Initialize database
    init_database()

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Write PID file
    write_pid()

    # Start HTTP server
    port = settings.get('SERVER_PORT', DEFAULT_PORT)
    server = HTTPServer(('127.0.0.1', port), APIHandler)
    server.timeout = 1  # Allow checking shutdown_event

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
