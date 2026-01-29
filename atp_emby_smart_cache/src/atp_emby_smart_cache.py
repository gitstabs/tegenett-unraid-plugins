"""
ATP Emby Smart Cache - Python Daemon v2026.01.29
SQLite-backed state management with preserved file operation logic
Author: Tegenett
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import threading
import json
import sqlite3
import signal
import urllib.request
import urllib.error
import glob
from pathlib import Path
from urllib.parse import urljoin, parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from contextlib import contextmanager
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

class Config:
    PLUGIN_NAME = "atp_emby_smart_cache"
    CONFIG_DIR = "/boot/config/plugins/atp_emby_smart_cache"
    DATA_DIR = "/mnt/user/appdata/atp_emby_smart_cache"
    DB_FILE = "state.db"
    SETTINGS_FILE = "settings.json"
    HIDDEN_SUFFIX = ".moved_to_cache"
    PARTIAL_SUFFIX = ".partial"

    # DEFAULTS - All paths are generic, user MUST configure these
    DEFAULTS = {
        "ENABLED": False,  # Disabled until configured
        "EMBY_HOST": "",   # User must set: http://YOUR_EMBY_IP:8096
        "EMBY_API_KEY": "",  # User must set: Get from Emby Dashboard > API Keys
        "DISCORD_WEBHOOK_URL": "",
        "SERVER_PORT": 9999,
        "UNRAID_USER_PATH": "/mnt/user",
        "CACHE_PATH": "/mnt/cache",  # Generic default
        "ARRAY_ONLY_PATH": "/mnt/user0",
        "LOG_FILE_PATH": "/mnt/user/appdata/atp_emby_smart_cache/logs/atp_emby_smart_cache.log",
        "RSYNC_BWLIMIT": "0",  # 0 = unlimited
        "MIN_FREE_SPACE_GB": 100,
        "MAX_FILE_SIZE_GB": 0,
        "SKIP_HARDLINKS": True,
        "DELETE_ON_STOP": True,
        "CLEANUP_DELAY_HOURS": 24,
        "MOVER_IGNORE_FILE": "",
        "ALLOWED_EXTS": ".mkv,.mp4,.m4v,.avi,.mov,.ts",
        "EXCLUDE_PATHS": "",
        "DOCKER_PATH_MAP": "",  # User must set if using Docker paths
        "COOLDOWN_MOVIE_SEC": 60,
        "COOLDOWN_EPISODE_SEC": 30,
        "PRECACHE_EPISODES": 1,
        "RSYNC_RETRIES": 3,
        "LOG_RETENTION": 5,
        "LOG_LEVEL": "INFO"
    }
    
    C = DEFAULTS.copy()
    ALLOWED_EXTS_SET = set()
    ALLOWED_SUB_EXTS = {'.srt', '.sub', '.idx', '.vtt', '.ass', '.smi'}
    EXCLUDE_LIST = []
    PATH_MAP = {}
    
    # SAFETY: Valid mount point prefixes (prevents writing to RAM)
    VALID_MOUNT_PREFIXES = [
        "/mnt/user",
        "/mnt/cache",
        "/mnt/disk",
        "/mnt/user0",
        "/mnt/remotes",
    ]
    
    @classmethod
    def validate_path(cls, path_str):
        """
        CRITICAL SAFETY CHECK: Validate that a path is on a real disk mount.
        Returns True if valid, False if path could write to RAM.
        """
        path_str = str(path_str)
        if not path_str.startswith("/mnt/"):
            return False
        for prefix in cls.VALID_MOUNT_PREFIXES:
            if path_str.startswith(prefix):
                return True
        return False

    @classmethod
    def load(cls):
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "logs"), exist_ok=True)
        
        path = os.path.join(cls.CONFIG_DIR, cls.SETTINGS_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    cls.C.update(json.load(f))
            except Exception as e:
                print(f"Config load error: {e}")
        
        # Type conversions
        try: cls.C["SERVER_PORT"] = int(cls.C["SERVER_PORT"])
        except: cls.C["SERVER_PORT"] = 9999
        try: cls.C["COOLDOWN_MOVIE_SEC"] = int(cls.C["COOLDOWN_MOVIE_SEC"])
        except: cls.C["COOLDOWN_MOVIE_SEC"] = 60
        try: cls.C["COOLDOWN_EPISODE_SEC"] = int(cls.C["COOLDOWN_EPISODE_SEC"])
        except: cls.C["COOLDOWN_EPISODE_SEC"] = 30
        try: cls.C["PRECACHE_EPISODES"] = int(cls.C["PRECACHE_EPISODES"])
        except: cls.C["PRECACHE_EPISODES"] = 1
        try: cls.C["RSYNC_RETRIES"] = int(cls.C["RSYNC_RETRIES"])
        except: cls.C["RSYNC_RETRIES"] = 3
        try: cls.C["MIN_FREE_SPACE_GB"] = int(cls.C["MIN_FREE_SPACE_GB"])
        except: cls.C["MIN_FREE_SPACE_GB"] = 300
        try: cls.C["MAX_FILE_SIZE_GB"] = float(cls.C["MAX_FILE_SIZE_GB"])
        except: cls.C["MAX_FILE_SIZE_GB"] = 0.0
        try: cls.C["CLEANUP_DELAY_HOURS"] = float(cls.C["CLEANUP_DELAY_HOURS"])
        except: cls.C["CLEANUP_DELAY_HOURS"] = 24.0
        
        bw = str(cls.C.get("RSYNC_BWLIMIT", "50000")).strip()
        cls.C["RSYNC_BWLIMIT"] = bw if bw.isdigit() else "50000"
        
        cls.ALLOWED_EXTS_SET = set(x.strip().lower() for x in cls.C.get("ALLOWED_EXTS", "").split(',') if x.strip())
        cls.EXCLUDE_LIST = [x.strip() for x in cls.C.get("EXCLUDE_PATHS", "").split(',') if x.strip()]
        
        cls.PATH_MAP = {}
        if cls.C.get("DOCKER_PATH_MAP"):
            for pair in cls.C["DOCKER_PATH_MAP"].split(','):
                if ':' in pair:
                    parts = pair.split(':', 1)
                    if len(parts) == 2:
                        cls.PATH_MAP[parts[0].strip()] = parts[1].strip()

Config.load()

# ============================================
# LOGGING
# ============================================

LOG_FILE = Config.C.get('LOG_FILE_PATH', '/var/log/atp_emby_smart_cache.log')
if os.path.isdir(LOG_FILE):
    LOG_FILE = os.path.join(LOG_FILE, "atp_emby_smart_cache.log")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Get log level from config
_log_level_str = Config.C.get('LOG_LEVEL', 'INFO').upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)

logging.basicConfig(
    filename=LOG_FILE,
    level=_log_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(_log_level)
console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)

START_TIME = time.time()

# ============================================
# DATABASE
# ============================================

class Database:
    def __init__(self):
        self.db_path = os.path.join(Config.DATA_DIR, Config.DB_FILE)
        # Use RLock to allow re-entrant locking (same thread can acquire multiple times)
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        with self._conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS managed_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_path TEXT UNIQUE NOT NULL,
                    cache_path TEXT,
                    array_path TEXT,
                    filename TEXT,
                    size_bytes INTEGER DEFAULT 0,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cleanup_at TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS cleanup_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_path TEXT UNIQUE NOT NULL,
                    filename TEXT,
                    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cleanup_time TIMESTAMP NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    filename TEXT,
                    path TEXT,
                    details TEXT
                );
                
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_managed_user ON managed_files(user_path);
                CREATE INDEX IF NOT EXISTS idx_queue_user ON cleanup_queue(user_path);
                CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_log(action);
                CREATE INDEX IF NOT EXISTS idx_activity_action_time ON activity_log(action, timestamp);
            ''')
            
            # Initialize stats if not exist
            conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_moves', '0')")
            conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_gb_moved', '0.0')")
            conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('last_move_date', '')")
    
    @contextmanager
    def _conn(self):
        acquired = self.lock.acquire(timeout=30)
        if not acquired:
            logger.error("DB: Could not acquire lock within 30 seconds!")
            raise Exception("Database lock timeout")
        try:
            conn = sqlite3.connect(self.db_path, timeout=30, isolation_level='DEFERRED')
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            try:
                yield conn
                conn.commit()
            except Exception as e:
                logger.error(f"DB: Rolling back due to error: {e}")
                conn.rollback()
                raise
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            self.lock.release()
    
    def add_managed_file(self, user_path, cache_path, array_path, filename, size_bytes, log_action='copy'):
        with self._conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO managed_files 
                (user_path, cache_path, array_path, filename, size_bytes, cached_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (str(user_path), str(cache_path), str(array_path), filename, size_bytes))
        # Log activity AFTER connection is closed (use specified action type)
        if log_action:
            self._log_activity(log_action, filename, str(user_path), f"Size: {size_bytes/(2**30):.2f} GB")
    
    def remove_managed_file(self, user_path):
        filename = None
        with self._conn() as conn:
            row = conn.execute("SELECT filename FROM managed_files WHERE user_path = ?", (str(user_path),)).fetchone()
            if row:
                filename = row['filename']
                conn.execute("DELETE FROM managed_files WHERE user_path = ?", (str(user_path),))
        # Log activity AFTER connection is closed to avoid nested locks
        if filename:
            self._log_activity('cleanup', filename, str(user_path), 'File removed from cache')
            return True
        return False
    
    def get_managed_files(self):
        with self._conn() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM managed_files ORDER BY cached_at DESC"
            ).fetchall()]
    
    def is_managed(self, user_path):
        with self._conn() as conn:
            return conn.execute(
                "SELECT 1 FROM managed_files WHERE user_path = ?", (str(user_path),)
            ).fetchone() is not None
    
    def schedule_cleanup(self, user_path, filename, delay_hours):
        cleanup_time = time.time() + (delay_hours * 3600)
        with self._conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO cleanup_queue (user_path, filename, cleanup_time)
                VALUES (?, ?, datetime(?, 'unixepoch'))
            ''', (str(user_path), filename, cleanup_time))
    
    def remove_from_queue(self, user_path):
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM cleanup_queue WHERE user_path = ?", (str(user_path),))
            return cursor.rowcount > 0
    
    def get_cleanup_queue(self):
        with self._conn() as conn:
            return [dict(row) for row in conn.execute('''
                SELECT *, strftime('%s', cleanup_time) as cleanup_time_unix
                FROM cleanup_queue ORDER BY cleanup_time ASC
            ''').fetchall()]
    
    def get_pending_cleanups(self):
        with self._conn() as conn:
            return [dict(row) for row in conn.execute('''
                SELECT * FROM cleanup_queue 
                WHERE cleanup_time <= datetime('now')
            ''').fetchall()]
    
    def update_stats(self, filename, size_gb):
        with self._conn() as conn:
            # Increment total moves
            conn.execute('''
                UPDATE stats SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) 
                WHERE key = 'total_moves'
            ''')
            # Add to total GB
            current = float(conn.execute("SELECT value FROM stats WHERE key = 'total_gb_moved'").fetchone()[0])
            conn.execute("UPDATE stats SET value = ? WHERE key = 'total_gb_moved'", (str(current + size_gb),))
            # Update last move date
            conn.execute("UPDATE stats SET value = ? WHERE key = 'last_move_date'", 
                        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
    
    def get_stats(self):
        with self._conn() as conn:
            stats = {}
            for row in conn.execute("SELECT key, value FROM stats").fetchall():
                stats[row['key']] = row['value']
            managed_count = conn.execute("SELECT COUNT(*) FROM managed_files").fetchone()[0]
            queue_count = conn.execute("SELECT COUNT(*) FROM cleanup_queue").fetchone()[0]
            total_size = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM managed_files").fetchone()[0]
            stats['managed_count'] = managed_count
            stats['queue_count'] = queue_count
            stats['total_cached_bytes'] = total_size
            return stats
    
    def _log_activity(self, action, filename, path, details=''):
        try:
            with self._conn() as conn:
                conn.execute('''
                    INSERT INTO activity_log (action, filename, path, details)
                    VALUES (?, ?, ?, ?)
                ''', (action, filename, path, details))
                # Keep only last 1000 entries
                conn.execute('''
                    DELETE FROM activity_log WHERE id NOT IN (
                        SELECT id FROM activity_log ORDER BY timestamp DESC LIMIT 1000
                    )
                ''')
        except Exception as e:
            logger.error(f"Activity log error: {e}")
    
    def get_activity(self, limit=50):
        with self._conn() as conn:
            return [dict(row) for row in conn.execute('''
                SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?
            ''', (limit,)).fetchall()]
    
    def get_statistics(self):
        """Get comprehensive statistics for the Statistics tab"""
        stats = {
            'total_moves': 0,
            'total_gb': 0,
            'last_move': '-',
            'avg_size_gb': 0,
            'daily_activity': [],
            'daily_storage': [],
            'top_files': []
        }
        
        try:
            with self._conn() as conn:
                # Total moves (copy actions only - not recovery)
                row = conn.execute("SELECT COUNT(*) as cnt FROM activity_log WHERE action = 'copy'").fetchone()
                stats['total_moves'] = row['cnt'] if row else 0
                
                # Last move timestamp
                row = conn.execute("SELECT timestamp FROM activity_log WHERE action = 'copy' ORDER BY timestamp DESC LIMIT 1").fetchone()
                if row:
                    stats['last_move'] = row['timestamp']
                
                # Total GB from current managed files (this is accurate)
                row = conn.execute("SELECT SUM(size_bytes) as total FROM managed_files").fetchone()
                if row and row['total']:
                    stats['total_gb'] = row['total'] / (2**30)
                
                # Average file size from current managed files
                row = conn.execute("SELECT AVG(size_bytes) as avg FROM managed_files").fetchone()
                if row and row['avg']:
                    stats['avg_size_gb'] = row['avg'] / (2**30)
                
                # Daily activity for last 7 days
                rows = conn.execute('''
                    SELECT DATE(timestamp) as date,
                           SUM(CASE WHEN action = 'copy' THEN 1 ELSE 0 END) as copies,
                           SUM(CASE WHEN action = 'cleanup' THEN 1 ELSE 0 END) as cleanups
                    FROM activity_log
                    WHERE timestamp >= DATE('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                ''').fetchall()
                stats['daily_activity'] = [{'date': r['date'], 'copies': r['copies'], 'cleanups': r['cleanups']} for r in rows]
                
                # Daily storage - parse size from details field ("Size: X.XX GB")
                rows = conn.execute('''
                    SELECT DATE(timestamp) as date, details
                    FROM activity_log
                    WHERE action = 'copy' AND timestamp >= DATE('now', '-7 days')
                ''').fetchall()
                
                daily_gb = {}
                for r in rows:
                    date = r['date']
                    details = r['details'] or ''
                    # Parse "Size: X.XX GB" from details
                    try:
                        if 'Size:' in details:
                            size_str = details.split('Size:')[1].strip().split()[0]
                            size_gb = float(size_str)
                            daily_gb[date] = daily_gb.get(date, 0) + size_gb
                    except:
                        pass
                
                stats['daily_storage'] = [{'date': d, 'gb': round(g, 2)} for d, g in sorted(daily_gb.items())]
                
                # Top 10 most cached files with actual sizes
                rows = conn.execute('''
                    SELECT filename, COUNT(*) as count, details
                    FROM activity_log
                    WHERE action = 'copy' AND filename IS NOT NULL
                    GROUP BY filename
                    ORDER BY count DESC
                    LIMIT 10
                ''').fetchall()
                
                top_files = []
                for r in rows:
                    # Parse size from most recent details
                    details = r['details'] or ''
                    size_gb = 0
                    try:
                        if 'Size:' in details:
                            size_str = details.split('Size:')[1].strip().split()[0]
                            size_gb = float(size_str)
                    except:
                        pass
                    top_files.append({
                        'filename': r['filename'],
                        'count': r['count'],
                        'total_gb': round(size_gb * r['count'], 2)
                    })
                stats['top_files'] = top_files
                
        except Exception as e:
            logger.error(f"Statistics error: {e}")
        
        return stats
    
    def clear_all(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM managed_files")
            conn.execute("DELETE FROM cleanup_queue")
    
    def reset_activity_log(self):
        """Clear activity log and reset statistics counters"""
        with self._conn() as conn:
            conn.execute("DELETE FROM activity_log")
            conn.execute("UPDATE stats SET value = '0' WHERE key = 'total_moves'")
            conn.execute("UPDATE stats SET value = '0.0' WHERE key = 'total_gb_moved'")
            conn.execute("UPDATE stats SET value = '' WHERE key = 'last_move_date'")
        logger.info("Activity log and statistics reset")

DB = Database()

# ============================================
# PATH TOOLS (PRESERVED FROM v2.22d)
# ============================================

class PathTools:
    @staticmethod
    def map_path(p):
        p = str(p)
        for d, h in Config.PATH_MAP.items():
            if p.startswith(d):
                return Path(p.replace(d, h, 1))
        return Path(p)
    
    @staticmethod
    def get_cache(p):
        s = str(p)
        if s.startswith(Config.C["UNRAID_USER_PATH"]):
            return Path(s.replace(Config.C["UNRAID_USER_PATH"], Config.C["CACHE_PATH"], 1))
        return None
    
    @staticmethod
    def get_array(p):
        s = str(p)
        if s.startswith(Config.C["UNRAID_USER_PATH"]):
            return Path(s.replace(Config.C["UNRAID_USER_PATH"], Config.C["ARRAY_ONLY_PATH"], 1))
        return None
    
    @staticmethod
    def get_user(p):
        s = str(p)
        if s.startswith(Config.C["CACHE_PATH"]):
            return Path(s.replace(Config.C["CACHE_PATH"], Config.C["UNRAID_USER_PATH"], 1))
        if s.startswith(Config.C["ARRAY_ONLY_PATH"]):
            return Path(s.replace(Config.C["ARRAY_ONLY_PATH"], Config.C["UNRAID_USER_PATH"], 1))
        return Path(p)

# ============================================
# MOVER IGNORE MANAGEMENT
# ============================================

class MoverIgnore:
    LOCK = threading.Lock()
    
    @staticmethod
    def add(path):
        f = Config.C["MOVER_IGNORE_FILE"]
        if not f:
            return
        user_path = str(PathTools.get_user(path))
        try:
            with MoverIgnore.LOCK:
                lines = set()
                if os.path.exists(f):
                    with open(f, 'r') as fp:
                        lines = set(l.strip() for l in fp if l.strip())
                if user_path not in lines:
                    with open(f, 'a') as fp:
                        fp.write(user_path + "\n")
                    logger.info(f"MoverIgnore added: {user_path}")
        except Exception as e:
            logger.error(f"MoverIgnore.add error: {e}")
    
    @staticmethod
    def remove(path):
        f = Config.C["MOVER_IGNORE_FILE"]
        if not f or not os.path.exists(f):
            return
        user_path = str(PathTools.get_user(path))
        try:
            with MoverIgnore.LOCK:
                with open(f, 'r') as fp:
                    lines = [l.strip() for l in fp if l.strip()]
                if user_path in lines:
                    with open(f, 'w') as fp:
                        for l in lines:
                            if l != user_path:
                                fp.write(l + "\n")
                    logger.info(f"MoverIgnore removed: {user_path}")
        except Exception as e:
            logger.error(f"MoverIgnore.remove error: {e}")
    
    @staticmethod
    def get_content():
        f = Config.C["MOVER_IGNORE_FILE"]
        if f and os.path.exists(f):
            try:
                with open(f, 'r') as fp:
                    return fp.read()
            except:
                pass
        return ""

# ============================================
# NOTIFICATION MANAGER
# ============================================

class Notify:
    COLORS = {
        "GREEN": 5763719,
        "YELLOW": 16776960,
        "ORANGE": 15105570,
        "RED": 15548997,
        "GREY": 9807270
    }
    
    def send(self, title, desc, color):
        url = Config.C["DISCORD_WEBHOOK_URL"]
        if not url:
            return
        data = {
            "embeds": [{
                "title": title,
                "description": desc,
                "color": color,
                "footer": {"text": "Emby Smart Cache V3.0"},
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }]
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            logger.error(f"Discord notification error: {e}")

NOTIFY = Notify()

# ============================================
# CACHE MANAGER (CORE LOGIC PRESERVED)
# ============================================

class CacheManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = set()
        self.active_lock = threading.Lock()
        self.processed = set()
        self.processed_lock = threading.Lock()
        self._cleanup_partials()
        self._recover_state()
    
    def _cleanup_partials(self):
        """Remove orphaned .partial files"""
        try:
            cache = Config.C["CACHE_PATH"]
            if not os.path.exists(cache):
                return
            for p in Path(cache).rglob("*" + Config.PARTIAL_SUFFIX):
                try:
                    if time.time() - p.stat().st_mtime > 3600:
                        p.unlink()
                        logger.info(f"Removed orphan partial: {p.name}")
                except:
                    pass
        except Exception as e:
            logger.error(f"Partial cleanup error: {e}")
    
    def _recover_state(self):
        """Scan for .moved_to_cache files and rebuild database state"""
        logger.info("State recovery starting...")
        logger.debug(f"Scanning array path: {Config.C['ARRAY_ONLY_PATH']}")
        count = 0
        try:
            array_path = Config.C["ARRAY_ONLY_PATH"]
            if not os.path.exists(array_path):
                logger.warning(f"Array path does not exist: {array_path}")
                return
            
            for hidden in Path(array_path).rglob("*" + Config.HIDDEN_SUFFIX):
                try:
                    logger.debug(f"Found marker: {hidden}")
                    base = hidden.name.replace(Config.HIDDEN_SUFFIX, "")
                    if Path(base).suffix.lower() in Config.ALLOWED_SUB_EXTS:
                        logger.debug(f"Skipping subtitle: {base}")
                        continue
                    
                    arr_orig = hidden.with_name(base)
                    user_path = PathTools.get_user(arr_orig)
                    cache_path = PathTools.get_cache(user_path)
                    
                    logger.debug(f"Paths: arr={arr_orig}, user={user_path}, cache={cache_path}")
                    
                    if not cache_path or not cache_path.exists():
                        logger.debug(f"Cache file missing: {cache_path}")
                        continue
                    
                    # Verify cache file integrity
                    size = cache_path.stat().st_size if cache_path.exists() else 0
                    if size == 0:
                        logger.warning(f"Cache file is empty: {cache_path}")
                        continue
                    
                    # Add to database and mover ignore (don't log as 'copy' - this is recovery)
                    DB.add_managed_file(user_path, cache_path, arr_orig, base, size, log_action=None)
                    MoverIgnore.add(user_path)
                    count += 1
                    logger.info(f"Recovered: {base}")
                    logger.debug(f"Recovered file size: {size / (2**30):.2f} GB")
                    
                except Exception as e:
                    logger.error(f"Recovery error for {hidden}: {e}")
            
            if count:
                logger.info(f"State recovery complete: {count} files recovered")
                NOTIFY.send("State Recovered", f"Found {count} managed files", NOTIFY.COLORS["GREEN"])
            else:
                logger.info("State recovery complete: no files found")
                
        except Exception as e:
            logger.error(f"State recovery error: {e}")
    
    def force_cleanup(self, user_path_str):
        """Force immediate cleanup of a cached file.
        
        CRITICAL SAFETY: This function checks for the ownership marker
        before deleting ANY file. If the marker (.moved_to_cache) does not
        exist on the array, the file is a NATIVE CACHE file and we must NOT
        delete it.
        """
        logger.info(f"Force cleanup requested: {user_path_str}")
        logger.debug(f"CACHE_PATH: {Config.C['CACHE_PATH']}")
        logger.debug(f"UNRAID_USER_PATH: {Config.C['UNRAID_USER_PATH']}")
        
        try:
            # Normalize path
            if user_path_str.startswith(Config.C["CACHE_PATH"]):
                user_path_str = user_path_str.replace(Config.C["CACHE_PATH"], Config.C["UNRAID_USER_PATH"])
                logger.debug(f"Path normalized from cache to user path")
            
            user_path = Path(user_path_str)
            logger.info(f"Normalized user_path: {user_path}")
            
            cache = PathTools.get_cache(user_path)
            arr = PathTools.get_array(user_path)
            logger.info(f"Cache path: {cache}")
            logger.info(f"Array path: {arr}")
            logger.debug(f"Cache exists: {cache.exists() if cache else False}")
            logger.debug(f"Array exists: {arr.exists() if arr else False}")
            
            # ============================================
            # CRITICAL SAFETY CHECK: Ownership Verification
            # ============================================
            if arr:
                hidden = arr.with_name(arr.name + Config.HIDDEN_SUFFIX)
                if not hidden.exists():
                    # NO MARKER = NATIVE CACHE FILE = DO NOT DELETE!
                    logger.warning(f"BLOCKED: Attempted force cleanup on NATIVE cache file (no marker): {user_path.name}")
                    logger.warning(f"  Expected marker at: {hidden}")
                    logger.warning(f"  This file was not moved by Emby Smart Cache. Cleanup aborted.")
                    return {'success': False, 'error': 'Cannot cleanup: This is a native cache file, not managed by Emby Smart Cache.'}
            else:
                logger.warning(f"BLOCKED: Cannot determine array path for: {user_path_str}")
                return {'success': False, 'error': 'Cannot determine array path'}
            
            # Marker exists - this is our managed file, safe to proceed
            logger.info(f"Ownership verified (marker exists): {hidden}")
            
            # Remove from queue and database
            logger.info("Removing from cleanup queue...")
            try:
                DB.remove_from_queue(user_path)
                logger.info("Removed from cleanup queue")
            except Exception as e:
                logger.error(f"Error removing from queue: {e}")
            
            logger.info("Removing from managed files...")
            try:
                DB.remove_managed_file(user_path)
                logger.info("Removed from managed files")
            except Exception as e:
                logger.error(f"Error removing from managed files: {e}")
            
            # Remove from mover ignore
            logger.info("Removing from mover ignore...")
            try:
                MoverIgnore.remove(user_path)
                logger.info("Removed from mover ignore")
            except Exception as e:
                logger.error(f"Error removing from mover ignore: {e}")
            
            # Restore hidden array file
            logger.info(f"Restoring hidden file: {hidden} -> {arr}")
            try:
                if hidden.exists():
                    os.rename(str(hidden), str(arr))
                    logger.info(f"Restored: {arr.name}")
                else:
                    logger.warning(f"Hidden file does not exist: {hidden}")
            except Exception as e:
                logger.error(f"Restore error: {e}")
            
            # Also restore subtitle files
            logger.info("Restoring subtitle files...")
            try:
                stem = arr.stem
                for f in arr.parent.iterdir():
                    if f.name.startswith(stem) and f.name.endswith(Config.HIDDEN_SUFFIX):
                        try:
                            orig_name = f.name[:-len(Config.HIDDEN_SUFFIX)]
                            orig = f.with_name(orig_name)
                            os.rename(str(f), str(orig))
                            logger.info(f"Restored subtitle: {orig_name}")
                            try:
                                MoverIgnore.remove(PathTools.get_user(orig))
                            except:
                                pass
                        except Exception as e:
                            logger.error(f"Subtitle restore error: {e}")
            except Exception as e:
                logger.error(f"Subtitle glob error: {e}")
            
            # Delete cache copy (NOW SAFE - we verified ownership)
            logger.info(f"Deleting cache copy: {cache}")
            if cache and cache.exists():
                try:
                    os.remove(str(cache))
                    logger.info(f"Deleted cache copy: {cache.name}")
                except Exception as e:
                    logger.error(f"Delete error: {e}")
                
                # Also delete cached subtitles
                logger.info("Deleting cached subtitles...")
                try:
                    stem = cache.stem
                    for f in cache.parent.iterdir():
                        if f.name.startswith(stem) and f.suffix.lower() in Config.ALLOWED_SUB_EXTS:
                            try:
                                os.remove(str(f))
                                logger.info(f"Deleted cached subtitle: {f.name}")
                                try:
                                    MoverIgnore.remove(PathTools.get_user(f))
                                except:
                                    pass
                            except Exception as e:
                                logger.error(f"Subtitle delete error: {e}")
                except Exception as e:
                    logger.error(f"Subtitle cleanup error: {e}")
            else:
                logger.warning(f"Cache file does not exist: {cache}")
            
            logger.info(f"Force cleanup complete: {user_path.name}")
            NOTIFY.send("Cleanup Complete", user_path.name, NOTIFY.COLORS["GREY"])
            return {'success': True, 'message': f'Cleanup complete: {user_path.name}'}
            
        except Exception as e:
            logger.error(f"Force cleanup failed with exception: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}
    
    def copy_file(self, path, item_id=None):
        """Copy a file to cache (main caching logic)"""
        logger.debug(f"copy_file called: path={path}, item_id={item_id}")
        
        if not Config.C["ENABLED"]:
            logger.debug("Plugin disabled, skipping")
            return
        
        # Check exclusions
        for ex in Config.EXCLUDE_LIST:
            if ex and ex in str(path):
                logger.debug(f"Path excluded by rule: {ex}")
                return
        
        # Check extension
        if path.suffix.lower() not in Config.ALLOWED_EXTS_SET:
            logger.debug(f"Extension not allowed: {path.suffix}")
            return
        
        # Check for parity operation
        try:
            with open("/proc/mdstat", "r") as f:
                if "resync" in f.read():
                    NOTIFY.send("System Busy", f"Parity check. Skip: {path.name}", NOTIFY.COLORS["ORANGE"])
                    logger.debug("Parity check in progress, skipping")
                    return
        except:
            pass
        
        arr = PathTools.get_array(path)
        cache = PathTools.get_cache(path)
        
        logger.debug(f"Computed paths: arr={arr}, cache={cache}")
        
        if not arr or not cache:
            logger.debug("Could not compute array or cache path")
            return
        
        # SAFETY: Validate cache path before any file operations
        if not Config.validate_path(str(cache)):
            logger.critical(f"CRITICAL: Invalid cache path: {cache}")
            logger.critical("This path could write to RAM! Aborting.")
            return
        
        # CRITICAL: Check hardlinks on ARRAY path, not user path
        if Config.C["SKIP_HARDLINKS"] and arr.exists():
            try:
                nlink = arr.stat().st_nlink
                if nlink > 1:
                    NOTIFY.send("Hardlink Skip", f"{path.name} ({nlink} links)", NOTIFY.COLORS["GREY"])
                    logger.info(f"SKIP hardlink: {path.name} has {nlink} links")
                    return
            except:
                pass
        
        # Remove from cleanup queue if re-playing
        if DB.remove_from_queue(path):
            NOTIFY.send("Resumed", path.name, NOTIFY.COLORS["GREEN"])
        
        # Check if already processed this session
        with self.processed_lock:
            if item_id:
                if item_id in self.processed:
                    return
                self.processed.add(item_id)
        
        # Get size from array file
        size_bytes = arr.stat().st_size if arr.exists() else 0
        size_gb = size_bytes / (2**30)
        
        # Check max file size
        if Config.C["MAX_FILE_SIZE_GB"] > 0 and size_gb > Config.C["MAX_FILE_SIZE_GB"]:
            logger.info(f"SKIP: Too large ({size_gb:.1f} GB > {Config.C['MAX_FILE_SIZE_GB']} GB)")
            return
        
        hidden = arr.with_name(arr.name + Config.HIDDEN_SUFFIX)
        
        # Check if already cached
        if cache.exists():
            if hidden.exists():
                # Managed cached file
                MoverIgnore.add(path)
                if not DB.is_managed(path):
                    # Re-add to database (don't log as new copy)
                    DB.add_managed_file(path, cache, arr, path.name, size_bytes, log_action=None)
                NOTIFY.send("Playing (Cached)", path.name, NOTIFY.COLORS["GREEN"])
            else:
                # Native cache file
                NOTIFY.send("Native Cache", f"Ignoring: {path.name}", NOTIFY.COLORS["GREY"])
            return
        
        # Check if source exists
        if not arr.exists():
            logger.warning(f"Source not found: {arr}")
            return
        
        # Check free space
        try:
            _, _, free = shutil.disk_usage(Config.C["CACHE_PATH"])
            required = Config.C["MIN_FREE_SPACE_GB"] + size_gb
            if (free / (2**30)) < required:
                NOTIFY.send("No Space", f"Skip: {path.name}", NOTIFY.COLORS["RED"])
                return
        except:
            pass
        
        # Mark as active
        with self.active_lock:
            if str(path) in self.active:
                return
            self.active.add(str(path))
        
        NOTIFY.send("Caching", f"{path.name} ({size_gb:.1f} GB)", NOTIFY.COLORS["YELLOW"])
        logger.info(f"Starting cache copy: {path.name}")
        
        # Start worker thread
        threading.Thread(
            target=self._worker,
            args=(path, cache, arr, size_bytes, size_gb),
            daemon=True
        ).start()
    
    def _worker(self, user_path, cache, arr, size_bytes, size_gb):
        """Worker thread for file copy operation (ATOMIC SWAP with ROLLBACK)"""
        tmp = cache.with_name(cache.name + Config.PARTIAL_SUFFIX)
        hidden = arr.with_name(arr.name + Config.HIDDEN_SUFFIX)
        start_time = time.time()
        max_retries = Config.C.get("RSYNC_RETRIES", 3)
        
        try:
            # Create cache directory
            cache.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy subtitles first
            try:
                for f in arr.parent.glob(glob.escape(arr.stem) + "*"):
                    if f.suffix.lower() in Config.ALLOWED_SUB_EXTS:
                        sub_dst = cache.with_name(f.name)
                        if not sub_dst.exists():
                            subprocess.run(["rsync", "-a", str(f), str(sub_dst)], 
                                         check=False, capture_output=True)
            except:
                pass
            
            # Main file copy via rsync WITH RETRY
            rsync_success = False
            last_error = ""
            
            for attempt in range(1, max_retries + 1):
                logger.info(f"Rsync attempt {attempt}/{max_retries}: {user_path.name}")
                
                cmd = [
                    "rsync", "-a", "--inplace", "--progress",
                    f"--bwlimit={Config.C['RSYNC_BWLIMIT']}",
                    str(arr), str(tmp)
                ]
                
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout
                    
                    if res.returncode == 0:
                        rsync_success = True
                        break
                    else:
                        last_error = res.stderr or f"Exit code {res.returncode}"
                        logger.warning(f"Rsync attempt {attempt} failed: {last_error}")
                        
                except subprocess.TimeoutExpired:
                    last_error = "Timeout (1 hour exceeded)"
                    logger.warning(f"Rsync attempt {attempt} timed out")
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Rsync attempt {attempt} exception: {e}")
                
                # Clean up failed attempt
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except:
                        pass
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
            
            if not rsync_success:
                logger.error(f"Rsync failed after {max_retries} attempts: {last_error}")
                NOTIFY.send("Copy Failed", f"{user_path.name}: {last_error[:30]}", NOTIFY.COLORS["RED"])
                return
            
            # Calculate speed
            elapsed = time.time() - start_time
            speed_mbps = (size_bytes / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            
            # Set permissions
            try:
                os.chmod(tmp, 0o666)
                shutil.chown(tmp, "nobody", "users")
            except:
                pass
            
            # ATOMIC SWAP WITH ROLLBACK
            try:
                # Step 1: Hide original
                os.rename(arr, hidden)
                
                # Step 2: Move partial to final (if this fails, rollback)
                try:
                    os.rename(tmp, cache)
                except Exception as e:
                    # ROLLBACK: Restore hidden file
                    logger.error(f"Rename failed, rolling back: {e}")
                    NOTIFY.send("Swap Failed", f"{user_path.name}: Rolling back", NOTIFY.COLORS["RED"])
                    if hidden.exists():
                        os.rename(hidden, arr)
                    if tmp.exists():
                        tmp.unlink()
                    raise
                    
            except Exception as e:
                logger.error(f"Atomic swap failed: {e}")
                return
            
            # Hide subtitle files too
            try:
                for f in arr.parent.glob(glob.escape(arr.stem) + "*"):
                    if f.suffix.lower() in Config.ALLOWED_SUB_EXTS:
                        sub_hid = f.with_name(f.name + Config.HIDDEN_SUFFIX)
                        try:
                            os.rename(f, sub_hid)
                            MoverIgnore.add(PathTools.get_user(cache.with_name(f.name)))
                        except:
                            pass
            except:
                pass
            
            # Add to mover ignore and database
            MoverIgnore.add(user_path)
            DB.add_managed_file(user_path, cache, arr, user_path.name, size_bytes)
            DB.update_stats(user_path.name, size_gb)
            
            # Success notification with speed
            NOTIFY.send("Cached", f"{user_path.name} ({size_gb:.1f}GB in {elapsed:.0f}s @ {speed_mbps:.1f}MB/s)", NOTIFY.COLORS["GREEN"])
            logger.info(f"Cache complete: {user_path.name} - {size_gb:.1f}GB in {elapsed:.0f}s ({speed_mbps:.1f} MB/s)")
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            NOTIFY.send("Cache Error", f"{user_path.name}: {str(e)[:30]}", NOTIFY.COLORS["RED"])
            if tmp.exists():
                try:
                    tmp.unlink()
                except:
                    pass
        finally:
            with self.active_lock:
                self.active.discard(str(user_path))
    
    def schedule_cleanup(self, path):
        """Schedule a file for cleanup after playback stops"""
        if not Config.C["DELETE_ON_STOP"]:
            return
        
        arr = PathTools.get_array(path)
        if arr:
            hidden = arr.with_name(arr.name + Config.HIDDEN_SUFFIX)
            if not hidden.exists():
                # This is a native cache file, not our managed file
                logger.info(f"Not scheduling (native cache): {path.name}")
                return
        
        delay = Config.C["CLEANUP_DELAY_HOURS"]
        DB.schedule_cleanup(path, path.name, delay)
        NOTIFY.send("Stopped", f"Cleanup in {delay}h: {path.name}", NOTIFY.COLORS["GREY"])
        logger.info(f"Scheduled cleanup: {path.name} in {delay}h")
    
    def process_queue(self):
        """Process pending cleanup queue"""
        for item in DB.get_pending_cleanups():
            try:
                logger.info(f"Processing scheduled cleanup: {item['filename']}")
                self.force_cleanup(item['user_path'])
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
    
    def is_cached(self, path):
        """Check if a file is currently cached"""
        cache = PathTools.get_cache(path)
        return cache and cache.exists()
    
    def get_active(self):
        """Get list of currently active transfers"""
        with self.active_lock:
            return list(self.active)

CM = CacheManager()

# ============================================
# PLAYBACK MONITOR
# ============================================

class Monitor:
    def __init__(self):
        self.active = set()
        self.lock = threading.Lock()
        self.headers = {
            "X-Emby-Token": Config.C["EMBY_API_KEY"],
            "Content-Type": "application/json"
        }
    
    def start(self, item_id, item_type):
        with self.lock:
            if item_id in self.active:
                return
            self.active.add(item_id)
        threading.Thread(target=self._run, args=(item_id, item_type), daemon=True).start()
    
    def _request(self, endpoint, retries=3):
        url = urljoin(Config.C["EMBY_HOST"], endpoint)
        for i in range(retries):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=10) as r:
                    return json.loads(r.read().decode())
            except:
                if i < retries - 1:
                    time.sleep(2 ** i)
        return None
    
    def _run(self, item_id, item_type):
        logger.info(f"Monitor started: {item_id} ({item_type})")
        logger.debug(f"Cooldown: Movie={Config.C['COOLDOWN_MOVIE_SEC']}s, Episode={Config.C['COOLDOWN_EPISODE_SEC']}s")
        session = None
        
        # Find the session
        for _ in range(5):
            sessions = self._request("/Sessions")
            if sessions:
                session = next(
                    (s for s in sessions 
                     if "NowPlayingItem" in s and s["NowPlayingItem"].get("Id") == item_id),
                    None
                )
                if session:
                    break
            time.sleep(1)
        
        if not session:
            logger.debug(f"Session not found for {item_id}")
            with self.lock:
                self.active.discard(item_id)
            return
        
        item = session["NowPlayingItem"]
        path = PathTools.map_path(item.get("Path", ""))
        user_id = session.get('UserId')
        series_id = item.get("SeriesId")
        
        logger.debug(f"Monitoring: {path.name if hasattr(path, 'name') else path}")
        
        # If already cached, just trigger copy_file (handles mover ignore etc) and return
        if CM.is_cached(path):
            logger.info(f"Already cached, skipping cooldown: {path.name if hasattr(path, 'name') else path}")
            CM.copy_file(path, item_id)
            with self.lock:
                self.active.discard(item_id)
            return
        
        # Wait for cooldown threshold BEFORE caching anything
        cooldown = Config.C["COOLDOWN_MOVIE_SEC"] if item_type == "Movie" else Config.C["COOLDOWN_EPISODE_SEC"]
        logger.info(f"Waiting for {cooldown}s cooldown before caching")
        
        cooldown_reached = False
        while True:
            sessions = self._request("/Sessions")
            if not sessions:
                time.sleep(10)
                continue
            
            session = next(
                (s for s in sessions 
                 if "NowPlayingItem" in s and s["NowPlayingItem"].get("Id") == item_id),
                None
            )
            
            if not session:
                logger.debug("Session ended before cooldown reached")
                break
            
            ps = session.get("PlayState", {})
            if ps.get("IsPaused"):
                logger.debug("Playback paused, waiting...")
                time.sleep(10)
                continue
            
            position_sec = ps.get("PositionTicks", 0) / 10000000
            logger.debug(f"Position: {position_sec:.0f}s / Cooldown: {cooldown}s")
            
            if position_sec >= cooldown:
                logger.info(f"Cooldown reached ({position_sec:.0f}s >= {cooldown}s), starting cache")
                cooldown_reached = True
                
                # Now cache the current file
                CM.copy_file(path, item_id)
                
                # Pre-fetch next episodes for TV shows (AFTER cooldown is reached)
                if item_type == "Episode" and Config.C["PRECACHE_EPISODES"] > 0:
                    self._precache_next_episodes(user_id, series_id, Config.C["PRECACHE_EPISODES"])
                
                break
            
            time.sleep(10)
        
        with self.lock:
            self.active.discard(item_id)
    
    def _precache_next_episodes(self, user_id, series_id, count):
        """Pre-cache the next N episodes in the series"""
        if not user_id or not series_id:
            return
        
        try:
            result = self._request(f"/Shows/NextUp?UserId={user_id}&SeriesId={series_id}&Limit={count}&Fields=Path")
            if result and "Items" in result:
                for i, n in enumerate(result["Items"]):
                    if n.get("Path"):
                        next_path = PathTools.map_path(n["Path"])
                        logger.info(f"Pre-caching next episode {i+1}/{count}: {n.get('Name', next_path.name if hasattr(next_path, 'name') else next_path)}")
                        CM.copy_file(next_path)
        except Exception as e:
            logger.error(f"Pre-cache error: {e}")
            NOTIFY.send("Pre-cache Error", str(e)[:50], NOTIFY.COLORS["RED"])

MON = Monitor()

# ============================================
# HTTP API HANDLER
# ============================================

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Suppress default logging
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _get_health_data(self):
        """Get system health metrics"""
        health = {}
        try:
            # Cache disk usage
            cache_path = Config.C.get('CACHE_PATH', '/mnt/cache_data')
            if os.path.exists(cache_path):
                stat = os.statvfs(cache_path)
                total = stat.f_blocks * stat.f_frsize
                free = stat.f_bavail * stat.f_frsize
                used = total - free
                health['cache_total_gb'] = total / (2**30)
                health['cache_used_gb'] = used / (2**30)
                health['cache_free_gb'] = free / (2**30)
                health['cache_used_pct'] = (used / total * 100) if total > 0 else 0
            
            # Array disk usage
            array_path = Config.C.get('ARRAY_ONLY_PATH', '/mnt/user0')
            if os.path.exists(array_path):
                stat = os.statvfs(array_path)
                total = stat.f_blocks * stat.f_frsize
                free = stat.f_bavail * stat.f_frsize
                used = total - free
                health['array_total_gb'] = total / (2**30)
                health['array_used_gb'] = used / (2**30)
                health['array_free_gb'] = free / (2**30)
                health['array_used_pct'] = (used / total * 100) if total > 0 else 0
            
            # Database size
            db_path = os.path.join(Config.DATA_DIR, Config.DB_FILE)
            if os.path.exists(db_path):
                size = os.path.getsize(db_path)
                if size < 1024:
                    health['db_size'] = f"{size} B"
                elif size < 1024 * 1024:
                    health['db_size'] = f"{size/1024:.1f} KB"
                else:
                    health['db_size'] = f"{size/(1024*1024):.1f} MB"
            else:
                health['db_size'] = '-'
            
            # Log file size
            log_path = Config.C.get('LOG_FILE_PATH', '')
            if log_path and os.path.exists(log_path):
                size = os.path.getsize(log_path)
                if size < 1024:
                    health['log_size'] = f"{size} B"
                elif size < 1024 * 1024:
                    health['log_size'] = f"{size/1024:.1f} KB"
                else:
                    health['log_size'] = f"{size/(1024*1024):.1f} MB"
            else:
                health['log_size'] = '-'
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
        
        return health
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        try:
            if path == '/api/status':
                stats = DB.get_stats()
                self._send_json({
                    'success': True,
                    'data': {
                        'running': True,
                        'uptime': time.time() - START_TIME,
                        'active': CM.get_active(),
                        'active_count': len(CM.get_active()),
                        'queue_count': stats.get('queue_count', 0),
                        'managed_count': stats.get('managed_count', 0),
                        'total_gb': stats.get('total_cached_bytes', 0) / (2**30),
                        'total_moves': int(stats.get('total_moves', 0)),
                        'total_gb_moved': float(stats.get('total_gb_moved', 0))
                    }
                })
            
            elif path == '/api/managed':
                files = DB.get_managed_files()
                result = []
                for f in files:
                    result.append({
                        'path': f['user_path'],
                        'filename': f['filename'],
                        'size_gb': (f['size_bytes'] or 0) / (2**30),
                        'cached_at': f['cached_at'],
                        'cleanup_at': f.get('cleanup_at')
                    })
                self._send_json({'success': True, 'data': result})
            
            elif path == '/api/queue':
                queue = DB.get_cleanup_queue()
                result = []
                for q in queue:
                    result.append({
                        'path': q['user_path'],
                        'filename': q['filename'],
                        'scheduled_at': q['scheduled_at'],
                        'cleanup_time': float(q.get('cleanup_time_unix', 0))
                    })
                self._send_json({'success': True, 'data': result})
            
            elif path == '/api/logs':
                lines = int(query.get('lines', [100])[0])
                log_content = ""
                if os.path.exists(LOG_FILE):
                    try:
                        result = subprocess.run(
                            ['tail', '-n', str(lines), LOG_FILE],
                            capture_output=True, text=True
                        )
                        log_content = result.stdout
                    except:
                        with open(LOG_FILE, 'r') as f:
                            log_content = '\n'.join(f.readlines()[-lines:])
                self._send_json({'success': True, 'logs': log_content})
            
            elif path == '/api/mover_ignore':
                self._send_json({'success': True, 'content': MoverIgnore.get_content()})
            
            elif path == '/api/history':
                activity = DB.get_activity(50)
                self._send_json({'success': True, 'data': activity})
            
            elif path == '/api/health':
                health = self._get_health_data()
                self._send_json({'success': True, 'data': health})
            
            elif path == '/api/stats':
                stats = DB.get_statistics()
                self._send_json({'success': True, 'data': stats})
            
            else:
                self._send_json({'success': False, 'error': 'Unknown endpoint'}, 404)
                
        except Exception as e:
            logger.error(f"GET error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)
    
    def do_POST(self):
        try:
            length = int(self.headers.get('content-length', 0))
            data = {}
            if length > 0:
                try:
                    data = json.loads(self.rfile.read(length).decode())
                except:
                    pass
            
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path == '/api/cleanup':
                if data.get('path'):
                    result = CM.force_cleanup(data['path'])
                    if isinstance(result, dict):
                        self._send_json(result)
                    else:
                        self._send_json({'success': True, 'message': 'Cleanup complete'})
                else:
                    self._send_json({'success': False, 'error': 'No path specified'}, 400)
            
            elif path == '/api/rebuild':
                DB.clear_all()
                CM._recover_state()
                self._send_json({'success': True, 'message': 'State rebuilt successfully'})
            
            elif path == '/api/reset_stats':
                DB.reset_activity_log()
                self._send_json({'success': True, 'message': 'Statistics reset successfully'})
            
            elif path == '/api/get_queue':
                # Legacy endpoint compatibility
                queue_dict = {}
                for q in DB.get_cleanup_queue():
                    queue_dict[q['user_path']] = float(q.get('cleanup_time_unix', 0))
                self._send_json({'success': True, 'message': queue_dict})
            
            elif path == '/api/force_cleanup':
                # Legacy endpoint compatibility
                if data.get('path'):
                    result = CM.force_cleanup(data['path'])
                    if isinstance(result, dict):
                        self._send_json(result)
                    else:
                        self._send_json({'success': True, 'message': 'Cleanup executed'})
                else:
                    self._send_json({'success': False, 'error': 'No path'}, 400)
            
            elif path == '/api/rebuild_state':
                # Legacy endpoint compatibility
                DB.clear_all()
                CM._recover_state()
                self._send_json({'success': True, 'message': 'State rebuild complete'})
            
            else:
                # Emby webhook handler
                event = data.get("Event")
                item = data.get("Item", {})
                
                logger.debug(f"WEBHOOK received: event={event}, item_type={item.get('Type')}, item_name={item.get('Name')}")
                
                if event == "playback.start" and item.get("Type") in ["Movie", "Episode"]:
                    logger.info(f"WEBHOOK: Playback start - {item.get('Name')}")
                    logger.debug(f"Item details: Id={item.get('Id')}, Path={item.get('Path')}")
                    MON.start(item.get("Id"), item.get("Type"))
                
                elif event == "playback.stop" and item.get("Path"):
                    path = PathTools.map_path(item["Path"])
                    logger.info(f"WEBHOOK: Playback stop - {item.get('Name')}")
                    logger.debug(f"Mapped path: {path}")
                    CM.schedule_cleanup(path)
                
                self._send_json({'success': True, 'message': 'OK'})
                
        except Exception as e:
            logger.error(f"POST error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)

# ============================================
# MAIN
# ============================================

shutdown_event = threading.Event()

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    shutdown_event.set()

def maintenance_loop():
    """Background maintenance loop - runs every 5 minutes"""
    while not shutdown_event.is_set():
        try:
            CM.process_queue()
        except Exception as e:
            logger.error(f"Maintenance error: {e}")
        
        # Sleep for 5 minutes (300 seconds) in small intervals
        for _ in range(300):
            if shutdown_event.is_set():
                break
            time.sleep(1)

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Reload config
    Config.load()
    
    # Log configuration for debugging
    logger.info("=" * 50)
    logger.info("Emby Smart Cache v3.2.0 starting...")
    logger.info(f"CACHE_PATH: {Config.C['CACHE_PATH']}")
    logger.info(f"ARRAY_ONLY_PATH: {Config.C['ARRAY_ONLY_PATH']}")
    logger.info(f"SERVER_PORT: {Config.C['SERVER_PORT']}")
    logger.info(f"LOG_LEVEL: {Config.C.get('LOG_LEVEL', 'INFO')}")
    
    # SAFETY: Validate critical paths at startup
    cache_path = Config.C["CACHE_PATH"]
    if not Config.validate_path(cache_path):
        logger.critical(f"CRITICAL: CACHE_PATH '{cache_path}' is not a valid Unraid mount!")
        logger.critical("This could write to RAM and fill it up. Please fix settings.json")
        logger.critical("Valid paths start with: /mnt/user, /mnt/cache, /mnt/disk, /mnt/user0, /mnt/remotes")
        sys.exit(1)
    else:
        logger.info(f"Path validation passed for: {cache_path}")
    
    # Start maintenance thread
    maint_thread = threading.Thread(target=maintenance_loop, daemon=True)
    maint_thread.start()
    
    port = Config.C["SERVER_PORT"]
    logger.info(f"Starting HTTP server on port {port}...")
    NOTIFY.send("Started", f"v3.2.0 on port {port}", NOTIFY.COLORS["GREEN"])
    
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
        server.timeout = 1
        logger.info(f"HTTP server successfully bound to 0.0.0.0:{port}")
        logger.info("Ready to accept connections")
        
        while not shutdown_event.is_set():
            try:
                server.handle_request()
            except Exception as req_e:
                logger.error(f"Request handling error: {req_e}")
            
    except OSError as e:
        if "Address already in use" in str(e):
            logger.critical(f"FATAL: Port {port} is already in use!")
            logger.critical("Another instance may be running. Try: pkill -f atp_emby_smart_cache.py")
        else:
            logger.critical(f"FATAL: Cannot bind to port {port}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"FATAL: {e}")
        sys.exit(1)
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
