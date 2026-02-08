#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATP Backup - Python Daemon v2026.01.28
Smart backup solution for Unraid with local, remote SMB, WOL, and cloud support
Author: Tegenett
"""

import os
import sys
import time
import json
import sqlite3
import logging
import signal
import socket
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# ============================================
# CONFIGURATION
# ============================================

class Config:
    PLUGIN_NAME = "atp_backup"
    CONFIG_DIR = f"/boot/config/plugins/{PLUGIN_NAME}"
    DATA_DIR = f"/mnt/user/appdata/{PLUGIN_NAME}"
    DB_FILE = "atp_backup.db"
    SETTINGS_FILE = "settings.json"
    PID_FILE = f"/var/run/{PLUGIN_NAME}.pid"
    VERSION = "2026.01.30e"
    
    DEFAULTS = {
        "ENABLED": True,
        "SERVER_PORT": 39982,
        "LOG_LEVEL": "INFO",
        "LOG_MAX_LINES": 10000,
        "DISCORD_WEBHOOK_URL": "",
        "DISCORD_NOTIFY_START": True,
        "DISCORD_NOTIFY_SUCCESS": True,
        "DISCORD_NOTIFY_FAILURE": True,
        "DISCORD_DAILY_SUMMARY": False,
        "DISCORD_SUMMARY_HOUR": 20,
        "UNRAID_NOTIFICATIONS": True,
        "DEFAULT_BANDWIDTH_LIMIT": 0,
        # Bandwidth scheduling (two profiles with start times)
        "BANDWIDTH_SCHEDULE_ENABLED": False,
        "BANDWIDTH_PROFILE_A_LIMIT": 0,       # 0 = unlimited (typically night)
        "BANDWIDTH_PROFILE_A_START": "22:00", # Night profile starts at 22:00
        "BANDWIDTH_PROFILE_B_LIMIT": 50000,   # 50 MB/s during day
        "BANDWIDTH_PROFILE_B_START": "06:00", # Day profile starts at 06:00
        "RSYNC_OPTIONS": "-avh --delete --stats --progress",
        "UD_MOUNT_TIMEOUT": 60,
        "WOL_WAIT_TIMEOUT": 120,
        "WOL_PING_INTERVAL": 5,
        "SMB_SETTLE_TIME": 10,
        "RETRY_ON_FAILURE": True,
        "RETRY_INTERVAL_MINUTES": 60,
        "RETRY_MAX_ATTEMPTS": 3,
        "HISTORY_RETENTION_DAYS": 90,
        # Discord summary reports (weekly/monthly)
        "DISCORD_WEEKLY_SUMMARY": False,
        "DISCORD_WEEKLY_DAY": 0,              # 0=Monday, 6=Sunday
        "DISCORD_WEEKLY_HOUR": 9,             # 09:00
        "DISCORD_MONTHLY_SUMMARY": False,
        "DISCORD_MONTHLY_DAY": 1,             # 1st of month
        "DISCORD_MONTHLY_HOUR": 9             # 09:00
    }
    
    C = DEFAULTS.copy()
    
    @classmethod
    def load(cls):
        """Load configuration from settings.json"""
        os.makedirs(cls.CONFIG_DIR, exist_ok=True)
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(cls.DATA_DIR, "logs"), exist_ok=True)
        
        path = os.path.join(cls.CONFIG_DIR, cls.SETTINGS_FILE)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    cls.C.update(loaded)
            except Exception as e:
                print(f"[Config] Load error: {e}")
        
        # Type conversions
        int_keys = ["SERVER_PORT", "LOG_MAX_LINES", "DISCORD_SUMMARY_HOUR", 
                    "DEFAULT_BANDWIDTH_LIMIT", "UD_MOUNT_TIMEOUT", 
                    "WOL_WAIT_TIMEOUT", "WOL_PING_INTERVAL", "SMB_SETTLE_TIME",
                    "RETRY_INTERVAL_MINUTES", "RETRY_MAX_ATTEMPTS"]
        for key in int_keys:
            try:
                cls.C[key] = int(cls.C.get(key, cls.DEFAULTS.get(key, 0)))
            except (ValueError, TypeError):
                cls.C[key] = cls.DEFAULTS.get(key, 0)
        
        # Boolean conversions
        bool_keys = ["ENABLED", "DISCORD_DAILY_SUMMARY", "UNRAID_NOTIFICATIONS", "RETRY_ON_FAILURE"]
        for key in bool_keys:
            val = cls.C.get(key, cls.DEFAULTS.get(key, False))
            if isinstance(val, str):
                cls.C[key] = val.lower() in ('true', '1', 'yes')
            else:
                cls.C[key] = bool(val)
    
    @classmethod
    def save(cls):
        """Save current configuration to settings.json"""
        path = os.path.join(cls.CONFIG_DIR, cls.SETTINGS_FILE)
        try:
            with open(path, 'w') as f:
                json.dump(cls.C, f, indent=2)
            return True, "Settings saved"
        except Exception as e:
            return False, str(e)

Config.load()


# ============================================
# BANDWIDTH SCHEDULER
# ============================================

class BandwidthScheduler:
    """Calculates effective bandwidth limit based on time-of-day profiles"""

    @staticmethod
    def get_effective_limit(job_limit=0):
        """
        Get the effective bandwidth limit considering:
        1. Job-specific limit (highest priority if > 0)
        2. Scheduled profile limit (if scheduling enabled)
        3. Default limit (fallback)

        Returns: bandwidth limit in KB/s (0 = unlimited)
        """
        # If job has specific limit, use it
        if job_limit and int(job_limit) > 0:
            return int(job_limit)

        # Check if scheduling is enabled
        if not Config.C.get("BANDWIDTH_SCHEDULE_ENABLED", False):
            return int(Config.C.get("DEFAULT_BANDWIDTH_LIMIT", 0) or 0)

        # Get current time
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        # Parse profile start times
        try:
            a_start = Config.C.get("BANDWIDTH_PROFILE_A_START", "22:00")
            b_start = Config.C.get("BANDWIDTH_PROFILE_B_START", "06:00")

            a_parts = a_start.split(":")
            b_parts = b_start.split(":")

            a_minutes = int(a_parts[0]) * 60 + int(a_parts[1])
            b_minutes = int(b_parts[0]) * 60 + int(b_parts[1])
        except (ValueError, IndexError):
            # Fallback to default if parsing fails
            return int(Config.C.get("DEFAULT_BANDWIDTH_LIMIT", 0) or 0)

        # Determine which profile is active
        # Profile A: from A_START to B_START
        # Profile B: from B_START to A_START

        a_limit = int(Config.C.get("BANDWIDTH_PROFILE_A_LIMIT", 0) or 0)
        b_limit = int(Config.C.get("BANDWIDTH_PROFILE_B_LIMIT", 0) or 0)

        if a_minutes < b_minutes:
            # Simple case: A starts before B (e.g., A=06:00, B=22:00)
            if a_minutes <= current_minutes < b_minutes:
                return a_limit
            else:
                return b_limit
        else:
            # Wrapped case: A starts after B (e.g., A=22:00, B=06:00)
            # Profile A is active from 22:00 to 23:59 and 00:00 to 06:00
            if current_minutes >= a_minutes or current_minutes < b_minutes:
                return a_limit
            else:
                return b_limit

    @staticmethod
    def get_current_profile():
        """Get the name of the currently active profile"""
        if not Config.C.get("BANDWIDTH_SCHEDULE_ENABLED", False):
            return "Default"

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        try:
            a_start = Config.C.get("BANDWIDTH_PROFILE_A_START", "22:00")
            b_start = Config.C.get("BANDWIDTH_PROFILE_B_START", "06:00")

            a_parts = a_start.split(":")
            b_parts = b_start.split(":")

            a_minutes = int(a_parts[0]) * 60 + int(a_parts[1])
            b_minutes = int(b_parts[0]) * 60 + int(b_parts[1])
        except (ValueError, IndexError):
            return "Default"

        if a_minutes < b_minutes:
            if a_minutes <= current_minutes < b_minutes:
                return "Profile A (Night)"
            else:
                return "Profile B (Day)"
        else:
            if current_minutes >= a_minutes or current_minutes < b_minutes:
                return "Profile A (Night)"
            else:
                return "Profile B (Day)"

# ============================================
# LOGGING
# ============================================

from logging.handlers import RotatingFileHandler

LOG_FILE = os.path.join(Config.DATA_DIR, "logs", f"{Config.PLUGIN_NAME}.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

_log_level_str = Config.C.get('LOG_LEVEL', 'INFO').upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)

# Log rotation settings from config
_log_max_size = int(Config.C.get('LOG_MAX_SIZE_KB', 5000)) * 1024  # Default 5MB
_log_keep_count = int(Config.C.get('LOG_KEEP_COUNT', 5))

# Create logger - use unique name and prevent propagation to root
logger = logging.getLogger(f"{Config.PLUGIN_NAME}_daemon")

# Only add handlers if not already added (prevents duplicates on reload)
if not logger.handlers:
    logger.setLevel(_log_level)
    logger.propagate = False  # Critical: prevents duplicate logs from root logger
    
    # Rotating file handler - automatically rotates when file exceeds max size
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=_log_max_size, 
        backupCount=_log_keep_count
    )
    file_handler.setLevel(_log_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
    logger.addHandler(file_handler)

# ============================================
# LOG MANAGER
# ============================================

class LogManager:
    """Manage log files and rotation"""
    
    @staticmethod
    def get_log_files():
        """Get list of all log files with sizes"""
        log_dir = os.path.dirname(LOG_FILE)
        log_files = []
        
        if os.path.exists(log_dir):
            for f in os.listdir(log_dir):
                if f.startswith(Config.PLUGIN_NAME):
                    path = os.path.join(log_dir, f)
                    size = os.path.getsize(path)
                    log_files.append({'name': f, 'size': size, 'path': path})
        
        return sorted(log_files, key=lambda x: x['name'])
    
    @staticmethod
    def get_total_log_size():
        """Get total size of all log files"""
        return sum(f['size'] for f in LogManager.get_log_files())
    
    @staticmethod
    def rotate_now():
        """Force immediate log rotation"""
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                handler.doRollover()
                logger.info("[LogManager] Log rotated manually")
                return True
        return False
    
    @staticmethod
    def clear_old_logs():
        """Delete all rotated log files (keep only current)"""
        log_dir = os.path.dirname(LOG_FILE)
        deleted = 0
        
        for f in os.listdir(log_dir):
            if f.startswith(Config.PLUGIN_NAME) and f != os.path.basename(LOG_FILE):
                try:
                    os.remove(os.path.join(log_dir, f))
                    deleted += 1
                except Exception as e:
                    logger.warning(f"[LogManager] Failed to delete {f}: {e}")
        
        logger.info(f"[LogManager] Cleared {deleted} old log files")
        return deleted

START_TIME = time.time()

# ============================================
# DATABASE WITH MIGRATION
# ============================================

class Database:
    # Schema version for migrations
    SCHEMA_VERSION = 4
    
    def __init__(self):
        self.db_path = os.path.join(Config.DATA_DIR, Config.DB_FILE)
        self.lock = threading.RLock()
        self._init_db()
        self._migrate_db()
    
    def _init_db(self):
        """Initialize database tables"""
        logger.info("[Database] Initializing database...")
        with self._conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS backup_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    job_type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    dest_path TEXT,
                    remote_host TEXT,
                    remote_share TEXT,
                    remote_mount_point TEXT,
                    remote_user TEXT,
                    remote_pass TEXT,
                    mac_address TEXT,
                    use_wol INTEGER DEFAULT 0,
                    shutdown_after INTEGER DEFAULT 0,
                    schedule_type TEXT DEFAULT 'disabled',
                    schedule_hour INTEGER DEFAULT 0,
                    schedule_minute INTEGER DEFAULT 0,
                    schedule_day INTEGER DEFAULT 0,
                    schedule_cron TEXT,
                    bandwidth_limit INTEGER DEFAULT 0,
                    exclude_patterns TEXT,
                    retention_count INTEGER DEFAULT 0,
                    retention_days INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    job_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    bytes_transferred INTEGER DEFAULT 0,
                    files_transferred INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    transfer_speed_mbps REAL DEFAULT 0,
                    error_message TEXT,
                    dry_run INTEGER DEFAULT 0,
                    log_output TEXT,
                    FOREIGN KEY (job_id) REFERENCES backup_jobs(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_jobs_run INTEGER DEFAULT 0,
                    successful_jobs INTEGER DEFAULT 0,
                    failed_jobs INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    total_files INTEGER DEFAULT 0,
                    total_duration INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );
                
                CREATE INDEX IF NOT EXISTS idx_history_job ON backup_history(job_id);
                CREATE INDEX IF NOT EXISTS idx_history_status ON backup_history(status);
                CREATE INDEX IF NOT EXISTS idx_history_started ON backup_history(started_at);
                CREATE INDEX IF NOT EXISTS idx_stats_date ON daily_stats(date);
            ''')
        logger.info("[Database] Initialization complete")
    
    def _migrate_db(self):
        """Run database migrations"""
        with self._conn() as conn:
            # Get current schema version
            try:
                row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
                current_version = row['version'] if row else 0
            except:
                current_version = 0
            
            logger.info(f"[Database] Current schema version: {current_version}, target: {self.SCHEMA_VERSION}")
            
            if current_version < 2:
                # Migration to v2: Add retry columns
                logger.info("[Database] Migrating to schema v2...")
                
                # Check if columns exist before adding
                columns = [row['name'] for row in conn.execute("PRAGMA table_info(backup_jobs)").fetchall()]
                
                if 'retry_on_failure' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN retry_on_failure INTEGER DEFAULT 1")
                    logger.info("[Database] Added retry_on_failure column")
                
                if 'retry_count' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN retry_count INTEGER DEFAULT 0")
                    logger.info("[Database] Added retry_count column")
                
                if 'last_retry_at' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN last_retry_at TIMESTAMP")
                    logger.info("[Database] Added last_retry_at column")
                
                # Check history table
                history_columns = [row['name'] for row in conn.execute("PRAGMA table_info(backup_history)").fetchall()]
                
                if 'is_retry' not in history_columns:
                    conn.execute("ALTER TABLE backup_history ADD COLUMN is_retry INTEGER DEFAULT 0")
                    logger.info("[Database] Added is_retry column to history")
                
                # Update schema version
                conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (2,))
                logger.info("[Database] Migration to v2 complete")
            
            if current_version < 3:
                # Migration to v3: Add pre/post script columns
                logger.info("[Database] Migrating to schema v3...")

                columns = [row['name'] for row in conn.execute("PRAGMA table_info(backup_jobs)").fetchall()]

                if 'pre_script' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN pre_script TEXT")
                    logger.info("[Database] Added pre_script column")

                if 'post_script' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN post_script TEXT")
                    logger.info("[Database] Added post_script column")

                conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (3,))
                logger.info("[Database] Migration to v3 complete")

            if current_version < 4:
                # Migration to v4: Add checksum verification column
                logger.info("[Database] Migrating to schema v4...")

                columns = [row['name'] for row in conn.execute("PRAGMA table_info(backup_jobs)").fetchall()]

                if 'verify_checksum' not in columns:
                    conn.execute("ALTER TABLE backup_jobs ADD COLUMN verify_checksum INTEGER DEFAULT 0")
                    logger.info("[Database] Added verify_checksum column")

                conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (4,))
                logger.info("[Database] Migration to v4 complete")
    
    @contextmanager
    def _conn(self):
        """Thread-safe database connection context manager"""
        acquired = self.lock.acquire(timeout=30)
        if not acquired:
            logger.error("[Database] Could not acquire lock within 30 seconds!")
            raise Exception("Database lock timeout")
        try:
            conn = sqlite3.connect(self.db_path, timeout=30, isolation_level='DEFERRED')
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            except Exception as e:
                logger.error(f"[Database] Rolling back due to error: {e}")
                conn.rollback()
                raise
            finally:
                conn.close()
        finally:
            self.lock.release()
    
    # ---- Job CRUD ----
    
    def get_jobs(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM backup_jobs ORDER BY name").fetchall()
            return [dict(row) for row in rows]
    
    def get_enabled_jobs(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM backup_jobs WHERE enabled = 1 ORDER BY name").fetchall()
            return [dict(row) for row in rows]
    
    def get_failed_jobs_for_retry(self):
        """Get jobs that failed and need retry"""
        with self._conn() as conn:
            max_retries = int(Config.C.get("RETRY_MAX_ATTEMPTS", 3) or 3)
            retry_interval = int(Config.C.get("RETRY_INTERVAL_MINUTES", 60) or 60)
            
            rows = conn.execute('''
                SELECT j.* FROM backup_jobs j
                INNER JOIN (
                    SELECT job_id, MAX(id) as last_id 
                    FROM backup_history 
                    GROUP BY job_id
                ) h ON j.id = h.job_id
                INNER JOIN backup_history bh ON bh.id = h.last_id
                WHERE j.enabled = 1 
                AND j.retry_on_failure = 1
                AND bh.status = 'failed'
                AND j.retry_count < ?
                AND (j.last_retry_at IS NULL OR 
                     datetime(j.last_retry_at, '+' || ? || ' minutes') <= datetime('now'))
            ''', (max_retries, retry_interval)).fetchall()
            return [dict(row) for row in rows]
    
    def get_job(self, job_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM backup_jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None
    
    def create_job(self, job_data):
        logger.info(f"[Database] Creating job: {job_data.get('name')}")
        with self._conn() as conn:
            cursor = conn.execute('''
                INSERT INTO backup_jobs (name, job_type, source_path, dest_path,
                    remote_host, remote_share, remote_mount_point, remote_user, remote_pass,
                    mac_address, use_wol, shutdown_after, schedule_type,
                    schedule_hour, schedule_minute, schedule_day, schedule_cron,
                    bandwidth_limit, exclude_patterns, retention_count, retention_days,
                    enabled, retry_on_failure, pre_script, post_script, verify_checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_data.get('name'),
                job_data.get('job_type', 'local'),
                job_data.get('source_path'),
                job_data.get('dest_path'),
                job_data.get('remote_host'),
                job_data.get('remote_share'),
                job_data.get('remote_mount_point'),
                job_data.get('remote_user'),
                job_data.get('remote_pass'),
                job_data.get('mac_address'),
                int(job_data.get('use_wol', 0)),
                int(job_data.get('shutdown_after', 0)),
                job_data.get('schedule_type', 'disabled'),
                int(job_data.get('schedule_hour', 0)),
                int(job_data.get('schedule_minute', 0)),
                int(job_data.get('schedule_day', 0)),
                job_data.get('schedule_cron'),
                int(job_data.get('bandwidth_limit', 0)),
                job_data.get('exclude_patterns'),
                int(job_data.get('retention_count', 0)),
                int(job_data.get('retention_days', 0)),
                int(job_data.get('enabled', 1)),
                int(job_data.get('retry_on_failure', 1)),
                job_data.get('pre_script'),
                job_data.get('post_script'),
                int(job_data.get('verify_checksum', 0))
            ))
            return cursor.lastrowid
    
    def update_job(self, job_id, job_data):
        logger.info(f"[Database] Updating job ID: {job_id}")
        with self._conn() as conn:
            conn.execute('''
                UPDATE backup_jobs SET
                    name = ?, job_type = ?, source_path = ?, dest_path = ?,
                    remote_host = ?, remote_share = ?, remote_mount_point = ?,
                    remote_user = ?, remote_pass = ?,
                    mac_address = ?, use_wol = ?, shutdown_after = ?, schedule_type = ?,
                    schedule_hour = ?, schedule_minute = ?, schedule_day = ?, schedule_cron = ?,
                    bandwidth_limit = ?, exclude_patterns = ?, retention_count = ?, retention_days = ?,
                    enabled = ?, retry_on_failure = ?, pre_script = ?, post_script = ?, verify_checksum = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                job_data.get('name'),
                job_data.get('job_type'),
                job_data.get('source_path'),
                job_data.get('dest_path'),
                job_data.get('remote_host'),
                job_data.get('remote_share'),
                job_data.get('remote_mount_point'),
                job_data.get('remote_user'),
                job_data.get('remote_pass'),
                job_data.get('mac_address'),
                int(job_data.get('use_wol', 0)),
                int(job_data.get('shutdown_after', 0)),
                job_data.get('schedule_type'),
                int(job_data.get('schedule_hour', 0)),
                int(job_data.get('schedule_minute', 0)),
                int(job_data.get('schedule_day', 0)),
                job_data.get('schedule_cron'),
                int(job_data.get('bandwidth_limit', 0)),
                job_data.get('exclude_patterns'),
                int(job_data.get('retention_count', 0)),
                int(job_data.get('retention_days', 0)),
                int(job_data.get('enabled', 1)),
                int(job_data.get('retry_on_failure', 1)),
                job_data.get('pre_script'),
                job_data.get('post_script'),
                int(job_data.get('verify_checksum', 0)),
                job_id
            ))
    
    def toggle_job(self, job_id, enabled):
        """Toggle job enabled/disabled status"""
        logger.info(f"[Database] Toggling job ID {job_id} to enabled={enabled}")
        with self._conn() as conn:
            conn.execute("UPDATE backup_jobs SET enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                        (int(enabled), job_id))
    
    def reset_retry_count(self, job_id):
        """Reset retry count after successful backup"""
        with self._conn() as conn:
            conn.execute("UPDATE backup_jobs SET retry_count = 0, last_retry_at = NULL WHERE id = ?", (job_id,))
    
    def increment_retry_count(self, job_id):
        """Increment retry count after failed retry"""
        with self._conn() as conn:
            conn.execute("""
                UPDATE backup_jobs 
                SET retry_count = retry_count + 1, last_retry_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (job_id,))
    
    def delete_job(self, job_id):
        logger.info(f"[Database] Deleting job ID: {job_id}")
        with self._conn() as conn:
            conn.execute("DELETE FROM backup_history WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM backup_jobs WHERE id = ?", (job_id,))
    
    # ---- History ----
    
    def add_history(self, job_id, job_name, status, dry_run=False, is_retry=False):
        with self._conn() as conn:
            cursor = conn.execute('''
                INSERT INTO backup_history (job_id, job_name, status, dry_run, is_retry)
                VALUES (?, ?, ?, ?, ?)
            ''', (job_id, job_name, status, 1 if dry_run else 0, 1 if is_retry else 0))
            return cursor.lastrowid
    
    def update_history(self, history_id, status, bytes_transferred=0, files_transferred=0,
                       duration_seconds=0, transfer_speed_mbps=0, error_message=None, log_output=None):
        with self._conn() as conn:
            conn.execute('''
                UPDATE backup_history SET
                    status = ?, finished_at = CURRENT_TIMESTAMP,
                    bytes_transferred = ?, files_transferred = ?,
                    duration_seconds = ?, transfer_speed_mbps = ?,
                    error_message = ?, log_output = ?
                WHERE id = ?
            ''', (status, bytes_transferred, files_transferred, duration_seconds,
                  transfer_speed_mbps, error_message, log_output, history_id))
    
    def get_history(self, limit=100, job_id=None, status=None):
        with self._conn() as conn:
            query = "SELECT * FROM backup_history WHERE 1=1"
            params = []
            
            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    def get_last_run(self, job_id):
        with self._conn() as conn:
            row = conn.execute('''
                SELECT * FROM backup_history 
                WHERE job_id = ?
                ORDER BY started_at DESC LIMIT 1
            ''', (job_id,)).fetchone()
            return dict(row) if row else None
    
    # ---- Statistics ----
    
    def update_daily_stats(self, bytes_transferred, files_transferred, duration, success):
        today = datetime.now().strftime('%Y-%m-%d')
        with self._conn() as conn:
            conn.execute('''
                INSERT INTO daily_stats (date, total_jobs_run, successful_jobs, failed_jobs,
                    total_bytes, total_files, total_duration)
                VALUES (?, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_jobs_run = total_jobs_run + 1,
                    successful_jobs = successful_jobs + ?,
                    failed_jobs = failed_jobs + ?,
                    total_bytes = total_bytes + ?,
                    total_files = total_files + ?,
                    total_duration = total_duration + ?
            ''', (today, 1 if success else 0, 0 if success else 1, bytes_transferred,
                  files_transferred, duration,
                  1 if success else 0, 0 if success else 1, bytes_transferred,
                  files_transferred, duration))
    
    def get_stats(self, days=30):
        with self._conn() as conn:
            rows = conn.execute('''
                SELECT * FROM daily_stats 
                WHERE date >= date('now', ?)
                ORDER BY date DESC
            ''', (f'-{days} days',)).fetchall()
            return [dict(row) for row in rows]
    
    def get_totals(self):
        with self._conn() as conn:
            row = conn.execute('''
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    COALESCE(SUM(bytes_transferred), 0) as total_bytes,
                    COALESCE(SUM(files_transferred), 0) as total_files,
                    COALESCE(SUM(duration_seconds), 0) as total_duration
                FROM backup_history
            ''').fetchone()
            return dict(row) if row else {}
    
    # ---- Database Management ----
    
    def clear_history(self):
        """Delete all backup history records"""
        logger.info("[Database] Clearing all backup history")
        with self._conn() as conn:
            conn.execute("DELETE FROM backup_history")
            logger.info("[Database] History cleared")
    
    def reset_statistics(self):
        """Reset all daily statistics"""
        logger.info("[Database] Resetting all statistics")
        with self._conn() as conn:
            conn.execute("DELETE FROM daily_stats")
            logger.info("[Database] Statistics reset")
    
    def reset_database(self):
        """Full database reset - clears history and statistics, keeps jobs"""
        logger.info("[Database] Full database reset starting")
        with self._conn() as conn:
            conn.execute("DELETE FROM backup_history")
            conn.execute("DELETE FROM daily_stats")
            # Reset retry counts on all jobs
            conn.execute("UPDATE backup_jobs SET retry_count = 0, last_retry_at = NULL")
            logger.info("[Database] Full database reset complete")

DB = Database()

# ============================================
# WAKE ON LAN
# ============================================

class WakeOnLan:
    @staticmethod
    def send_magic_packet(mac_address, broadcast_ip='255.255.255.255', port=9):
        try:
            mac = mac_address.replace(':', '').replace('-', '').replace('.', '').lower()
            if len(mac) != 12:
                raise ValueError(f"Invalid MAC address: {mac_address}")
            
            try:
                int(mac, 16)
            except ValueError:
                raise ValueError(f"Invalid MAC address (not hex): {mac_address}")
            
            mac_bytes = bytes.fromhex(mac)
            packet = b'\xff' * 6 + mac_bytes * 16
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_ip, port))
            sock.close()
            
            logger.info(f"[WOL] Sent magic packet to {mac_address}")
            return True, "Magic packet sent"
        except Exception as e:
            logger.error(f"[WOL] Failed to send magic packet: {e}")
            return False, str(e)
    
    @staticmethod
    def wait_for_host(host, timeout=120, interval=5):
        logger.info(f"[WOL] Waiting for {host} to come online (timeout: {timeout}s)")
        start = time.time()
        while time.time() - start < timeout:
            if WakeOnLan.ping(host):
                elapsed = int(time.time() - start)
                logger.info(f"[WOL] {host} is online after {elapsed}s")
                return True, elapsed
            time.sleep(interval)
        logger.warning(f"[WOL] Timeout waiting for {host}")
        return False, timeout
    
    @staticmethod
    def ping(host, timeout=2):
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), host],
                capture_output=True, timeout=timeout+2
            )
            return result.returncode == 0
        except:
            return False

# ============================================
# REMOTE SHUTDOWN
# ============================================

class RemoteShutdown:
    @staticmethod
    def shutdown_windows(host, username, password, timeout_seconds=30, force=True, message="Backup completed"):
        try:
            cmd = ['net', 'rpc', 'shutdown', '-I', host, '-U', f'{username}%{password}']
            
            if timeout_seconds > 0:
                cmd.extend(['-t', str(timeout_seconds)])
            
            if force:
                cmd.append('-f')
            
            if message:
                cmd.extend(['-C', message])
            
            logger.info(f"[RemoteShutdown] Sending shutdown to {host}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info(f"[RemoteShutdown] Shutdown command sent successfully to {host}")
                return True, "Shutdown command sent"
            else:
                error = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
                logger.error(f"[RemoteShutdown] Failed - {error}")
                return False, error
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError:
            return False, "Samba net command not found"
        except Exception as e:
            return False, str(e)

# ============================================
# MOUNT MANAGER
# ============================================

class MountManager:
    RC_PATHS = [
        '/usr/local/sbin/rc.unassigned',
        '/var/local/overlay/usr/local/sbin/rc.unassigned'
    ]
    
    @classmethod
    def get_rc_path(cls):
        for path in cls.RC_PATHS:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        return None
    
    @classmethod
    def is_ud_available(cls):
        return cls.get_rc_path() is not None
    
    @classmethod
    def mount(cls, share_name, timeout=60):
        rc_path = cls.get_rc_path()
        if not rc_path:
            return False, "Unassigned Devices plugin not installed"
        
        try:
            logger.info(f"[MountManager] Mounting {share_name}")
            result = subprocess.run(
                [rc_path, 'mount', share_name],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = (result.stdout + result.stderr).lower()
            
            if result.returncode == 0 or 'success' in output:
                logger.info(f"[MountManager] Mounted {share_name}")
                return True, "Mounted successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Mount failed"
                logger.error(f"[MountManager] Mount failed - {error}")
                return False, error
        except subprocess.TimeoutExpired:
            return False, f"Mount timed out after {timeout}s"
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def unmount(cls, share_name, timeout=30):
        rc_path = cls.get_rc_path()
        if not rc_path:
            return False, "Unassigned Devices plugin not installed"
        
        try:
            logger.info(f"[MountManager] Unmounting {share_name}")
            result = subprocess.run(
                [rc_path, 'umount', share_name],
                capture_output=True, text=True, timeout=timeout
            )
            
            output = (result.stdout + result.stderr).lower()
            
            if result.returncode == 0 or 'success' in output:
                logger.info(f"[MountManager] Unmounted {share_name}")
                return True, "Unmounted successfully"
            else:
                error = result.stderr.strip() or result.stdout.strip() or "Unmount failed"
                logger.error(f"[MountManager] Unmount failed - {error}")
                return False, error
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def is_mounted(cls, mount_point):
        try:
            result = subprocess.run(
                ['mountpoint', '-q', mount_point],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False

# ============================================
# NOTIFICATION MANAGER
# ============================================

class NotifyManager:
    COLORS = {
        "blue": 3447003,
        "green": 5763719,
        "red": 15548997,
        "orange": 15105570,
        "grey": 9807270
    }
    
    @classmethod
    def unraid_notify(cls, subject, description, importance="normal"):
        if not Config.C.get("UNRAID_NOTIFICATIONS", True):
            return True
        
        try:
            cmd = [
                '/usr/local/emhttp/webGui/scripts/notify',
                '-e', 'ATP Backup',
                '-s', subject,
                '-d', description,
                '-i', importance
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            logger.debug(f"[Notify] Unraid notification sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"[Notify] Unraid notification failed - {e}")
            return False
    
    @classmethod
    def discord_notify(cls, title, description, color="blue", fields=None, footer=None):
        url = Config.C.get("DISCORD_WEBHOOK_URL", "")
        if not url:
            logger.debug("[Notify] Discord webhook not configured")
            return True
        
        try:
            import urllib.request
            import ssl
            
            embed = {
                "title": title,
                "description": description,
                "color": cls.COLORS.get(color, cls.COLORS["grey"]),
                "footer": {"text": footer or f"ATP Backup v{Config.VERSION}"},
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            }
            
            if fields:
                embed["fields"] = fields
            
            data = json.dumps({"embeds": [embed]}).encode()
            
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': f'AtpBackup/{Config.VERSION}'
                }
            )
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                pass
            
            logger.info(f"[Notify] Discord notification sent: {title}")
            return True
        except Exception as e:
            logger.error(f"[Notify] Discord notification failed - {e}")
            return False
    
    @classmethod
    def send_daily_summary(cls):
        if not Config.C.get("DISCORD_DAILY_SUMMARY", False):
            return

        url = Config.C.get("DISCORD_WEBHOOK_URL", "")
        if not url:
            return

        today = datetime.now().strftime('%Y-%m-%d')
        stats = DB.get_stats(1)

        if not stats:
            return

        stat = stats[0]
        total = stat.get('total_jobs_run', 0)
        success = stat.get('successful_jobs', 0)
        failed = stat.get('failed_jobs', 0)
        total_bytes = stat.get('total_bytes', 0)

        gb = total_bytes / (1024**3) if total_bytes else 0

        color = "green" if failed == 0 else ("orange" if success > 0 else "red")

        cls.discord_notify(
            f"📊 Daily Summary - {today}",
            f"Total jobs: {total}\nSuccessful: {success}\nFailed: {failed}",
            color,
            [
                {"name": "Data Transferred", "value": f"{gb:.2f} GB", "inline": True},
                {"name": "Success Rate", "value": f"{(success/max(total,1))*100:.0f}%", "inline": True}
            ]
        )

    @classmethod
    def send_weekly_summary(cls):
        """Send weekly summary report"""
        if not Config.C.get("DISCORD_WEEKLY_SUMMARY", False):
            return

        url = Config.C.get("DISCORD_WEBHOOK_URL", "")
        if not url:
            return

        stats = DB.get_stats(7)

        if not stats:
            return

        # Aggregate weekly stats
        total = sum(s.get('total_jobs_run', 0) for s in stats)
        success = sum(s.get('successful_jobs', 0) for s in stats)
        failed = sum(s.get('failed_jobs', 0) for s in stats)
        total_bytes = sum(s.get('total_bytes', 0) for s in stats)
        total_duration = sum(s.get('total_duration', 0) for s in stats)

        gb = total_bytes / (1024**3) if total_bytes else 0
        hours = total_duration / 3600 if total_duration else 0

        color = "green" if failed == 0 else ("orange" if success > 0 else "red")

        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        week_end = datetime.now().strftime('%Y-%m-%d')

        cls.discord_notify(
            f"📈 Weekly Summary ({week_start} to {week_end})",
            f"Total jobs: {total}\nSuccessful: {success}\nFailed: {failed}",
            color,
            [
                {"name": "Data Transferred", "value": f"{gb:.2f} GB", "inline": True},
                {"name": "Success Rate", "value": f"{(success/max(total,1))*100:.0f}%", "inline": True},
                {"name": "Total Duration", "value": f"{hours:.1f} hours", "inline": True}
            ]
        )
        logger.info("[Notify] Weekly summary sent")

    @classmethod
    def send_monthly_summary(cls):
        """Send monthly summary report"""
        if not Config.C.get("DISCORD_MONTHLY_SUMMARY", False):
            return

        url = Config.C.get("DISCORD_WEBHOOK_URL", "")
        if not url:
            return

        stats = DB.get_stats(30)

        if not stats:
            return

        # Aggregate monthly stats
        total = sum(s.get('total_jobs_run', 0) for s in stats)
        success = sum(s.get('successful_jobs', 0) for s in stats)
        failed = sum(s.get('failed_jobs', 0) for s in stats)
        total_bytes = sum(s.get('total_bytes', 0) for s in stats)
        total_duration = sum(s.get('total_duration', 0) for s in stats)

        gb = total_bytes / (1024**3) if total_bytes else 0
        hours = total_duration / 3600 if total_duration else 0

        color = "green" if failed == 0 else ("orange" if success > 0 else "red")

        month_name = datetime.now().strftime('%B %Y')

        cls.discord_notify(
            f"📊 Monthly Summary - {month_name}",
            f"Total jobs: {total}\nSuccessful: {success}\nFailed: {failed}",
            color,
            [
                {"name": "Data Transferred", "value": f"{gb:.2f} GB", "inline": True},
                {"name": "Success Rate", "value": f"{(success/max(total,1))*100:.0f}%", "inline": True},
                {"name": "Total Duration", "value": f"{hours:.1f} hours", "inline": True}
            ]
        )
        logger.info("[Notify] Monthly summary sent")

# ============================================
# BACKUP ENGINE
# ============================================

class BackupEngine:
    current_job = None
    current_history_id = None
    current_progress = {}
    abort_flag = False
    _lock = threading.Lock()
    
    @classmethod
    def is_running(cls):
        with cls._lock:
            return cls.current_job is not None
    
    @classmethod
    def get_status(cls):
        with cls._lock:
            if cls.current_job:
                return {
                    'running': True,
                    'job_id': cls.current_job.get('id'),
                    'job_name': cls.current_job.get('name'),
                    'progress': cls.current_progress.copy()
                }
            return {'running': False}
    
    @classmethod
    def abort(cls):
        cls.abort_flag = True
        logger.warning("[BackupEngine] Abort requested")
    
    @staticmethod
    def _format_size(bytes_val):
        """Format bytes to human readable string"""
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.1f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
    
    @staticmethod
    def _format_speed(bytes_per_sec):
        """Format speed to human readable string"""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    
    @classmethod
    def _run_script(cls, script_path, script_type):
        """Run a pre/post backup script"""
        if not script_path:
            return True, None
        
        if not os.path.exists(script_path):
            return False, f"Script not found: {script_path}"
        
        if not os.access(script_path, os.X_OK):
            # Try to make it executable
            try:
                os.chmod(script_path, 0o755)
            except:
                return False, f"Script not executable: {script_path}"
        
        logger.info(f"[BackupEngine] Running {script_type} script: {script_path}")
        
        try:
            result = subprocess.run(
                [script_path],
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
                cwd=os.path.dirname(script_path)
            )
            
            if result.returncode == 0:
                logger.info(f"[BackupEngine] {script_type} script completed successfully")
                return True, None
            else:
                error = result.stderr or result.stdout or f"Exit code {result.returncode}"
                logger.error(f"[BackupEngine] {script_type} script failed: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Script timed out after 1 hour"
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def run_job(cls, job, dry_run=False, is_retry=False):
        with cls._lock:
            if cls.current_job:
                logger.warning("[BackupEngine] Cannot start job - another job is running")
                return False, "Another backup is already running"
            cls.current_job = job
            cls.current_progress = {'phase': 'starting', 'percent': 0}
            cls.abort_flag = False
        
        job_id = job['id']
        job_name = job['name']
        job_type = job['job_type']
        
        logger.info("=" * 60)
        logger.info(f"[BackupEngine] Starting job: {job_name}")
        logger.info(f"[BackupEngine] Type: {job_type}, Dry run: {dry_run}, Retry: {is_retry}")
        logger.info("=" * 60)
        
        history_id = DB.add_history(job_id, job_name, 'running', dry_run, is_retry)
        cls.current_history_id = history_id
        
        retry_text = " (Retry)" if is_retry else ""
        
        # Notify start if enabled
        if Config.C.get("DISCORD_NOTIFY_START", True):
            NotifyManager.discord_notify(
                f"🔄 Backup Started{retry_text}: {job_name}",
                f"Type: {job_type}\nDry run: {'Yes' if dry_run else 'No'}",
                "blue"
            )
        
        start_time = time.time()
        bytes_transferred = 0
        files_transferred = 0
        error_message = None
        log_output = ""
        success = False
        
        try:
            # Run pre-backup script if configured
            pre_script = job.get('pre_script')
            if pre_script and not dry_run:
                cls.current_progress['phase'] = 'pre-script'
                script_ok, script_error = cls._run_script(pre_script, 'pre-backup')
                if not script_ok:
                    error_message = f"Pre-backup script failed: {script_error}"
                    logger.error(f"[BackupEngine] {error_message}")
                    raise Exception(error_message)
            
            cls.current_progress['phase'] = 'running'
            
            if job_type == 'local':
                success, bytes_transferred, files_transferred, error_message, log_output = cls._run_local(job, dry_run)
            elif job_type == 'remote_smb':
                success, bytes_transferred, files_transferred, error_message, log_output = cls._run_remote_smb(job, dry_run)
            elif job_type == 'remote_smb_wol':
                success, bytes_transferred, files_transferred, error_message, log_output = cls._run_remote_smb_wol(job, dry_run)
            else:
                error_message = f"Unknown job type: {job_type}"
                logger.error(f"[BackupEngine] {error_message}")
            
            # Run post-backup script if configured and backup succeeded
            post_script = job.get('post_script')
            if post_script and not dry_run and success:
                cls.current_progress['phase'] = 'post-script'
                script_ok, script_error = cls._run_script(post_script, 'post-backup')
                if not script_ok:
                    logger.warning(f"[BackupEngine] Post-backup script failed: {script_error}")
                    # Don't fail the whole job for post-script failure
                    
        except Exception as e:
            error_message = str(e)
            logger.exception(f"[BackupEngine] Exception in job '{job_name}'")
        
        duration = int(time.time() - start_time)
        
        # Calculate speed in bytes/second, store as float for flexibility
        speed_bytes_per_sec = bytes_transferred / max(duration, 1)
        
        status = 'completed' if success else 'failed'
        DB.update_history(
            history_id, status, bytes_transferred, files_transferred,
            duration, speed_bytes_per_sec, error_message, log_output
        )
        
        if not dry_run:
            DB.update_daily_stats(bytes_transferred, files_transferred, duration, success)
        
        # Handle retry logic
        if success:
            DB.reset_retry_count(job_id)
        elif not dry_run and job.get('retry_on_failure', 1):
            DB.increment_retry_count(job_id)
        
        # Format size and speed for logging and notifications
        size_str = cls._format_size(bytes_transferred)
        speed_str = cls._format_speed(speed_bytes_per_sec)
        
        if success:
            logger.info(f"[BackupEngine] Job completed: {size_str} in {duration}s ({speed_str})")
            
            # Notify success if enabled
            if Config.C.get("DISCORD_NOTIFY_SUCCESS", True):
                NotifyManager.discord_notify(
                    f"✅ Backup Completed{retry_text}: {job_name}",
                    f"Duration: {duration}s\nTransferred: {size_str}" + (" (dry run)" if dry_run else ""),
                    "green",
                    [
                        {"name": "Files", "value": str(files_transferred), "inline": True},
                        {"name": "Speed", "value": speed_str, "inline": True}
                    ]
                )
            NotifyManager.unraid_notify(f"Backup OK: {job_name}", f"Transferred {size_str} in {duration}s")
        else:
            logger.error(f"[BackupEngine] Job failed: {error_message}")
            retry_info = ""
            if job.get('retry_on_failure', 1) and Config.C.get("RETRY_ON_FAILURE", True):
                retry_count = int(job.get('retry_count', 0) or 0) + 1
                max_retries = int(Config.C.get("RETRY_MAX_ATTEMPTS", 3) or 3)
                if retry_count < max_retries:
                    retry_interval = int(Config.C.get('RETRY_INTERVAL_MINUTES', 60) or 60)
                    retry_info = f"\n\n🔁 Will retry in {retry_interval} minutes ({retry_count}/{max_retries})"
            
            # Notify failure if enabled
            if Config.C.get("DISCORD_NOTIFY_FAILURE", True):
                NotifyManager.discord_notify(
                    f"❌ Backup Failed{retry_text}: {job_name}",
                    f"Error: {error_message or 'Unknown error'}{retry_info}",
                    "red"
                )
            NotifyManager.unraid_notify(f"Backup FAILED: {job_name}", error_message or "Unknown error", "alert")
        
        with cls._lock:
            cls.current_job = None
            cls.current_history_id = None
            cls.current_progress = {}
        
        logger.info("=" * 60)
        logger.info(f"[BackupEngine] Job finished: {job_name} - {status}")
        logger.info("=" * 60)
        
        return success, error_message
    
    @classmethod
    def _run_local(cls, job, dry_run):
        source = job.get('source_path', '')
        dest = job.get('dest_path', '')
        
        if not source:
            return False, 0, 0, "Source path not configured", ""
        if not dest:
            return False, 0, 0, "Destination path not configured", ""
        
        if not os.path.exists(source):
            return False, 0, 0, f"Source path does not exist: {source}", ""
        
        os.makedirs(dest, exist_ok=True)
        
        return cls._run_rsync(source, dest, job, dry_run)
    
    @classmethod
    def _run_remote_smb(cls, job, dry_run):
        source = job.get('source_path', '')
        remote_share = job.get('remote_share', '')
        mount_point = job.get('remote_mount_point', '')
        dest_subdir = job.get('dest_path', '')
        
        if not source:
            return False, 0, 0, "Source path not configured", ""
        if not remote_share:
            return False, 0, 0, "Remote share not configured", ""
        if not mount_point:
            return False, 0, 0, "Mount point not configured", ""
        
        if not MountManager.is_ud_available():
            return False, 0, 0, "Unassigned Devices plugin not installed", ""
        
        if not os.path.exists(source):
            return False, 0, 0, f"Source path does not exist: {source}", ""
        
        was_mounted = MountManager.is_mounted(mount_point)
        
        if not was_mounted:
            cls.current_progress['phase'] = 'mounting'
            success, msg = MountManager.mount(remote_share)
            if not success:
                return False, 0, 0, f"Failed to mount remote share: {msg}", ""
            
            time.sleep(Config.C.get('SMB_SETTLE_TIME', 10))
            
            if not MountManager.is_mounted(mount_point):
                return False, 0, 0, "Mount point not available after mount command", ""
        
        dest = os.path.join(mount_point, dest_subdir) if dest_subdir else mount_point
        os.makedirs(dest, exist_ok=True)
        
        cls.current_progress['phase'] = 'transferring'
        
        try:
            return cls._run_rsync(source, dest, job, dry_run)
        finally:
            if not was_mounted:
                cls.current_progress['phase'] = 'unmounting'
                MountManager.unmount(remote_share)
    
    @classmethod
    def _run_remote_smb_wol(cls, job, dry_run):
        host = job.get('remote_host', '')
        mac = job.get('mac_address', '')
        
        if not host:
            return False, 0, 0, "Remote host not configured", ""
        
        cls.current_progress['phase'] = 'checking host'
        host_was_online = WakeOnLan.ping(host)
        logger.info(f"[BackupEngine] Host {host} online: {host_was_online}")
        
        if not host_was_online:
            if not mac:
                return False, 0, 0, "Host offline and no MAC address configured for WOL", ""
            
            cls.current_progress['phase'] = 'sending WOL'
            success, msg = WakeOnLan.send_magic_packet(mac)
            if not success:
                return False, 0, 0, f"Failed to send WOL packet: {msg}", ""
            
            cls.current_progress['phase'] = 'waiting for host'
            timeout = Config.C.get("WOL_WAIT_TIMEOUT", 120)
            interval = Config.C.get("WOL_PING_INTERVAL", 5)
            online, elapsed = WakeOnLan.wait_for_host(host, timeout, interval)
            
            if not online:
                return False, 0, 0, f"Host did not come online within {timeout}s", ""
            
            smb_wait = Config.C.get("SMB_SETTLE_TIME", 10)
            logger.info(f"[BackupEngine] Waiting {smb_wait}s for SMB service...")
            time.sleep(smb_wait)
        
        success, bytes_transferred, files_transferred, error, log_output = cls._run_remote_smb(job, dry_run)
        
        if success and job.get('shutdown_after') and not host_was_online:
            user = job.get('remote_user', '')
            password = job.get('remote_pass', '')
            
            if user and password:
                cls.current_progress['phase'] = 'shutting down remote'
                logger.info(f"[BackupEngine] Sending shutdown to {host}")
                shutdown_ok, shutdown_msg = RemoteShutdown.shutdown_windows(host, user, password)
                if not shutdown_ok:
                    logger.warning(f"[BackupEngine] Shutdown failed: {shutdown_msg}")
            else:
                logger.info("[BackupEngine] Skipping shutdown - credentials not configured")
        
        return success, bytes_transferred, files_transferred, error, log_output
    
    @classmethod
    def _run_rsync(cls, source, dest, job, dry_run):
        cmd = ['rsync']
        
        options = Config.C.get("RSYNC_OPTIONS", "-avh --delete --stats")
        cmd.extend(options.split())
        
        # Get effective bandwidth limit (considers job setting, schedule, and default)
        job_bw = int(job.get('bandwidth_limit', 0) or 0)
        bw_limit = BandwidthScheduler.get_effective_limit(job_bw)
        if bw_limit > 0:
            cmd.append(f'--bwlimit={bw_limit}')
            logger.info(f"[BackupEngine] Bandwidth limit: {bw_limit} KB/s ({BandwidthScheduler.get_current_profile()})")

        # Checksum verification (slower but more accurate)
        if job.get('verify_checksum'):
            cmd.append('--checksum')
            logger.info("[BackupEngine] Checksum verification enabled")
        
        excludes = job.get('exclude_patterns', '') or ''
        for pattern in excludes.split('\n'):
            pattern = pattern.strip()
            if pattern and not pattern.startswith('#'):
                cmd.append(f'--exclude={pattern}')
        
        if dry_run:
            cmd.append('--dry-run')
        
        source = source.rstrip('/') + '/'
        cmd.extend([source, dest])
        
        logger.info(f"[BackupEngine] Rsync command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)
            
            output = result.stdout + '\n' + result.stderr
            
            bytes_transferred = 0
            files_transferred = 0
            
            def parse_bytes(s):
                """Parse bytes from rsync output, handling various formats.

                Rsync output formats:
                - "Total transferred file size: 8,710,422,528 bytes"
                - "Total transferred file size: 8.710.422.528 bytes" (some locales)
                - "Literal data: 8710422528 bytes"
                """
                if not s:
                    return 0
                s = s.strip()
                # Remove thousand separators (comma, period, space)
                # Rsync always outputs whole numbers for bytes, never decimals
                digits_only = re.sub(r'[^\d]', '', s)
                try:
                    return int(digits_only) if digits_only else 0
                except:
                    return 0

            # Parse rsync statistics - look for the best indicator of actual file size
            total_file_size = 0  # "Total file size" - total size of all files in source
            transferred_size = 0  # "Total transferred file size" - what was actually transferred
            literal_data = 0  # "Literal data" - actual bytes sent
            total_bytes_sent = 0  # "Total bytes sent" - includes protocol overhead
            total_bytes_received = 0  # "Total bytes received" - for pull operations
            progress_bytes_sum = 0  # Sum of file sizes from --progress output

            # Log raw output for debugging (first 2000 chars)
            logger.debug(f"[BackupEngine] Raw rsync output (first 2000 chars):\n{output[:2000]}")

            for line in output.split('\n'):
                line_lower = line.lower().strip()
                line_stripped = line.strip()

                # Primary: "Total transferred file size:" - best metric for actual backup size
                if 'total transferred file size:' in line_lower or 'total transferred file size' in line_lower:
                    # Extract everything after the colon
                    if ':' in line:
                        after_colon = line.split(':', 1)[1]
                        match = re.search(r'([\d,\.\s]+)', after_colon)
                        if match:
                            transferred_size = parse_bytes(match.group(1))
                            logger.info(f"[BackupEngine] Found 'Total transferred file size': {transferred_size}")

                # Secondary: "Total file size:" - total size of source (may differ from transferred)
                elif 'total file size:' in line_lower and 'transferred' not in line_lower:
                    if ':' in line:
                        after_colon = line.split(':', 1)[1]
                        match = re.search(r'([\d,\.\s]+)', after_colon)
                        if match:
                            total_file_size = parse_bytes(match.group(1))
                            logger.info(f"[BackupEngine] Found 'Total file size': {total_file_size}")

                # Tertiary: "Literal data:" - actual bytes transferred (without compression)
                elif 'literal data:' in line_lower:
                    if ':' in line:
                        after_colon = line.split(':', 1)[1]
                        match = re.search(r'([\d,\.\s]+)', after_colon)
                        if match:
                            literal_data = parse_bytes(match.group(1))
                            logger.info(f"[BackupEngine] Found 'Literal data': {literal_data}")

                # "Total bytes sent:" - includes protocol overhead
                elif 'total bytes sent:' in line_lower:
                    if ':' in line:
                        after_colon = line.split(':', 1)[1]
                        match = re.search(r'([\d,\.\s]+)', after_colon)
                        if match:
                            total_bytes_sent = parse_bytes(match.group(1))
                            logger.info(f"[BackupEngine] Found 'Total bytes sent': {total_bytes_sent}")

                # "Total bytes received:" - for pull/receive operations
                elif 'total bytes received:' in line_lower:
                    if ':' in line:
                        after_colon = line.split(':', 1)[1]
                        match = re.search(r'([\d,\.\s]+)', after_colon)
                        if match:
                            total_bytes_received = parse_bytes(match.group(1))
                            logger.info(f"[BackupEngine] Found 'Total bytes received': {total_bytes_received}")

                # Alternative format: "sent X bytes  received Y bytes" (single line)
                elif 'sent' in line_lower and 'bytes' in line_lower and 'received' in line_lower:
                    # Format: "sent 8,710,422,528 bytes  received 1,234 bytes  123.45 bytes/sec"
                    sent_match = re.search(r'sent\s+([\d,\.\s]+)\s*bytes', line, re.IGNORECASE)
                    if sent_match:
                        sent_val = parse_bytes(sent_match.group(1))
                        if sent_val > total_bytes_sent:
                            total_bytes_sent = sent_val
                            logger.info(f"[BackupEngine] Found 'sent X bytes': {total_bytes_sent}")

                # Parse --progress output: "116.83M 100%  43.96MB/s  0:00:02 (xfr#1, to-chk=113/1032)"
                # This shows the actual file size being transferred
                elif '100%' in line and '(xfr#' in line:
                    # Extract size from beginning of line: "116.83M 100%" or "21.97M 100%"
                    size_match = re.match(r'\s*([\d,\.]+)([KMGT]?)\s+100%', line_stripped)
                    if size_match:
                        size_num = float(size_match.group(1).replace(',', ''))
                        size_unit = size_match.group(2).upper()
                        multipliers = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
                        file_bytes = int(size_num * multipliers.get(size_unit, 1))
                        progress_bytes_sum += file_bytes

            # Log all parsed values for debugging
            logger.info(f"[BackupEngine] Parsed values: transferred={transferred_size}, total_file={total_file_size}, literal={literal_data}, sent={total_bytes_sent}, received={total_bytes_received}, progress_sum={progress_bytes_sum}")

            # Choose best available metric (priority order)
            # For incremental syncs, --progress output shows actual file sizes transferred
            # The stats section only shows delta bytes (often 0 for unchanged files)
            if progress_bytes_sum > 0:
                # Progress output is most accurate for files actually transferred
                bytes_transferred = progress_bytes_sum
                logger.info(f"[BackupEngine] Using progress_sum as bytes_transferred: {bytes_transferred}")
            elif transferred_size > 0:
                bytes_transferred = transferred_size
            elif total_file_size > 0:
                bytes_transferred = total_file_size
            elif literal_data > 0:
                bytes_transferred = literal_data
            elif total_bytes_sent > 0:
                bytes_transferred = total_bytes_sent
            elif total_bytes_received > 0:
                bytes_transferred = total_bytes_received

            for line in output.split('\n'):
                line_lower = line.lower()
                            
                # Files transferred
                if 'number of regular files transferred:' in line_lower:
                    match = re.search(r'(\d+)', line.split(':')[1] if ':' in line else line)
                    if match:
                        try:
                            files_transferred = int(match.group(1))
                        except:
                            pass
                elif 'number of files transferred:' in line_lower and files_transferred == 0:
                    match = re.search(r'(\d+)', line.split(':')[1] if ':' in line else line)
                    if match:
                        try:
                            files_transferred = int(match.group(1))
                        except:
                            pass
            
            # Log parsed values for debugging
            logger.info(f"[BackupEngine] Parsed stats: {files_transferred} files, {bytes_transferred} bytes")
            
            if result.returncode == 0:
                return True, bytes_transferred, files_transferred, None, output
            else:
                if result.returncode in [23, 24]:
                    logger.warning(f"[BackupEngine] Rsync completed with warnings (exit {result.returncode})")
                    return True, bytes_transferred, files_transferred, f"Completed with warnings (exit {result.returncode})", output
                
                error = f"Rsync failed with exit code {result.returncode}"
                return False, bytes_transferred, files_transferred, error, output
                
        except subprocess.TimeoutExpired:
            return False, 0, 0, "Rsync timed out after 24 hours", ""
        except Exception as e:
            return False, 0, 0, str(e), ""

# ============================================
# SCHEDULER
# ============================================

class Scheduler:
    _thread = None
    _running = False
    _stopped = False
    _last_run = {}
    _summary_sent_today = False
    _weekly_sent_this_week = False
    _monthly_sent_this_month = False
    
    @classmethod
    def start(cls):
        if cls._thread and cls._thread.is_alive():
            logger.warning("[Scheduler] Already running")
            return
        
        cls._running = True
        cls._stopped = False
        cls._thread = threading.Thread(target=cls._run, daemon=True, name="Scheduler")
        cls._thread.start()
        logger.info("[Scheduler] Started")
    
    @classmethod
    def stop(cls):
        if cls._stopped:
            return  # Prevent re-entry
        cls._stopped = True
        cls._running = False
        if cls._thread:
            cls._thread.join(timeout=5)
        logger.info("[Scheduler] Stopped")
    
    @classmethod
    def _run(cls):
        while cls._running:
            try:
                now = datetime.now()
                cls._check_daily_summary(now)
                cls._check_jobs(now)
                cls._check_retries()
            except Exception as e:
                logger.error(f"[Scheduler] Error in main loop: {e}")
            
            time.sleep(60)
    
    @classmethod
    def _check_daily_summary(cls, now):
        summary_hour = Config.C.get("DISCORD_SUMMARY_HOUR", 20)

        if now.hour == summary_hour and now.minute == 0:
            if not cls._summary_sent_today:
                NotifyManager.send_daily_summary()
                cls._summary_sent_today = True
        elif now.hour != summary_hour:
            cls._summary_sent_today = False

        # Check weekly summary
        weekly_day = int(Config.C.get("DISCORD_WEEKLY_DAY", 0))  # 0=Monday
        weekly_hour = int(Config.C.get("DISCORD_WEEKLY_HOUR", 9))

        if now.weekday() == weekly_day and now.hour == weekly_hour and now.minute == 0:
            if not cls._weekly_sent_this_week:
                NotifyManager.send_weekly_summary()
                cls._weekly_sent_this_week = True
        elif now.weekday() != weekly_day:
            cls._weekly_sent_this_week = False

        # Check monthly summary
        monthly_day = int(Config.C.get("DISCORD_MONTHLY_DAY", 1))
        monthly_hour = int(Config.C.get("DISCORD_MONTHLY_HOUR", 9))

        if now.day == monthly_day and now.hour == monthly_hour and now.minute == 0:
            if not cls._monthly_sent_this_month:
                NotifyManager.send_monthly_summary()
                cls._monthly_sent_this_month = True
        elif now.day != monthly_day:
            cls._monthly_sent_this_month = False
    
    @classmethod
    def _check_jobs(cls, now):
        if BackupEngine.is_running():
            return
        
        jobs = DB.get_enabled_jobs()
        
        for job in jobs:
            job_id = job['id']
            schedule_type = job.get('schedule_type', 'disabled')
            
            if schedule_type == 'disabled':
                continue
            
            if cls._should_run(job, now):
                last = cls._last_run.get(job_id)
                if last and (now - last).total_seconds() < 60:
                    continue
                
                cls._last_run[job_id] = now
                logger.info(f"[Scheduler] Starting scheduled job: {job['name']}")
                
                thread = threading.Thread(
                    target=BackupEngine.run_job,
                    args=(job, False, False),
                    name=f"Backup-{job['name']}"
                )
                thread.start()
                break
    
    @classmethod
    def _check_retries(cls):
        """Check for failed jobs that need retry"""
        if not Config.C.get("RETRY_ON_FAILURE", True):
            return
        
        if BackupEngine.is_running():
            return
        
        try:
            jobs = DB.get_failed_jobs_for_retry()
            
            for job in jobs:
                logger.info(f"[Scheduler] Retrying failed job: {job['name']} (attempt {job.get('retry_count', 0) + 1})")
                
                thread = threading.Thread(
                    target=BackupEngine.run_job,
                    args=(job, False, True),
                    name=f"Retry-{job['name']}"
                )
                thread.start()
                break
        except Exception as e:
            logger.error(f"[Scheduler] Error checking retries: {e}")
    
    @classmethod
    def _should_run(cls, job, now):
        schedule_type = job.get('schedule_type', 'disabled')
        hour = job.get('schedule_hour', 0)
        minute = job.get('schedule_minute', 0)
        day = job.get('schedule_day', 0)
        
        if schedule_type == 'hourly':
            return now.minute == minute
        elif schedule_type == 'daily':
            return now.hour == hour and now.minute == minute
        elif schedule_type == 'weekly':
            return now.weekday() == day and now.hour == hour and now.minute == minute
        elif schedule_type == 'custom':
            cron = job.get('schedule_cron', '')
            return cls._match_cron(cron, now)
        
        return False
    
    @classmethod
    def _match_cron(cls, cron_expr, dt):
        if not cron_expr:
            return False
        
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                return False
            
            minute, hour, day, month, weekday = parts
            
            checks = [
                (minute, dt.minute),
                (hour, dt.hour),
                (day, dt.day),
                (month, dt.month),
                (weekday, dt.weekday())
            ]
            
            for pattern, value in checks:
                if not cls._cron_match(pattern, value):
                    return False
            
            return True
        except:
            return False
    
    @classmethod
    def _cron_match(cls, pattern, value):
        if pattern == '*':
            return True
        
        if pattern.startswith('*/'):
            try:
                step = int(pattern[2:])
                return value % step == 0
            except:
                return False
        
        if ',' in pattern:
            values = [int(v) for v in pattern.split(',')]
            return value in values
        
        if '-' in pattern:
            try:
                start, end = pattern.split('-')
                return int(start) <= value <= int(end)
            except:
                return False
        
        try:
            return value == int(pattern)
        except:
            return False

# ============================================
# HTTP API SERVER
# ============================================

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.debug(f"[API] {args[0]}")
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def _read_json(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode())
        return {}
    
    def do_OPTIONS(self):
        self._send_json({'success': True})
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        try:
            if path == '/api/status':
                uptime = int(time.time() - START_TIME)
                status = BackupEngine.get_status()
                self._send_json({
                    'success': True,
                    'version': Config.VERSION,
                    'uptime': uptime,
                    'ud_available': MountManager.is_ud_available(),
                    'backup': status
                })
            
            elif path == '/api/jobs':
                jobs = DB.get_jobs()
                for job in jobs:
                    last = DB.get_last_run(job['id'])
                    job['last_run'] = last
                self._send_json({'success': True, 'jobs': jobs})
            
            elif path.startswith('/api/jobs/') and path.count('/') == 3:
                job_id = int(path.split('/')[-1])
                job = DB.get_job(job_id)
                if job:
                    job['last_run'] = DB.get_last_run(job_id)
                    self._send_json({'success': True, 'job': job})
                else:
                    self._send_json({'success': False, 'error': 'Job not found'}, 404)
            
            elif path == '/api/history':
                limit = int(params.get('limit', [100])[0])
                job_id = params.get('job_id', [None])[0]
                if job_id:
                    job_id = int(job_id)
                history = DB.get_history(limit, job_id)
                self._send_json({'success': True, 'history': history})
            
            elif path == '/api/stats':
                days = int(params.get('days', [30])[0])
                stats = DB.get_stats(days)
                totals = DB.get_totals()
                self._send_json({'success': True, 'stats': stats, 'totals': totals})
            
            elif path == '/api/logs':
                lines = int(params.get('lines', [200])[0])
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, 'r') as f:
                        all_lines = f.readlines()
                        log_content = ''.join(all_lines[-lines:])
                else:
                    log_content = "No log file found"
                self._send_json({'success': True, 'logs': log_content})
            
            elif path == '/api/settings':
                self._send_json({'success': True, 'settings': Config.C})

            elif path == '/api/export/jobs':
                # Export all jobs as JSON
                jobs = DB.get_jobs()
                # Remove sensitive fields for export
                for job in jobs:
                    job.pop('remote_pass', None)  # Don't export passwords
                    job.pop('id', None)  # Remove IDs (will be recreated on import)
                    job.pop('created_at', None)
                    job.pop('updated_at', None)
                    job.pop('retry_count', None)
                    job.pop('last_retry_at', None)
                export_data = {
                    'version': Config.VERSION,
                    'export_date': datetime.now().isoformat(),
                    'export_type': 'jobs',
                    'jobs': jobs
                }
                self._send_json({'success': True, 'data': export_data})

            elif path == '/api/export/settings':
                # Export settings (exclude sensitive data)
                settings = Config.C.copy()
                settings.pop('DISCORD_WEBHOOK_URL', None)  # Don't export webhook
                export_data = {
                    'version': Config.VERSION,
                    'export_date': datetime.now().isoformat(),
                    'export_type': 'settings',
                    'settings': settings
                }
                self._send_json({'success': True, 'data': export_data})

            elif path == '/api/bandwidth/status':
                # Get current bandwidth profile status
                self._send_json({
                    'success': True,
                    'scheduling_enabled': Config.C.get("BANDWIDTH_SCHEDULE_ENABLED", False),
                    'current_profile': BandwidthScheduler.get_current_profile(),
                    'effective_limit': BandwidthScheduler.get_effective_limit(0),
                    'profile_a': {
                        'start': Config.C.get("BANDWIDTH_PROFILE_A_START", "22:00"),
                        'limit': Config.C.get("BANDWIDTH_PROFILE_A_LIMIT", 0)
                    },
                    'profile_b': {
                        'start': Config.C.get("BANDWIDTH_PROFILE_B_START", "06:00"),
                        'limit': Config.C.get("BANDWIDTH_PROFILE_B_LIMIT", 0)
                    }
                })
            
            else:
                self._send_json({'success': False, 'error': 'Not found'}, 404)
                
        except Exception as e:
            logger.error(f"[API] GET error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)
    
    def do_POST(self):
        path = self.path
        
        try:
            data = self._read_json()
            
            if path == '/api/jobs':
                job_id = DB.create_job(data)
                self._send_json({'success': True, 'id': job_id})
            
            elif path.startswith('/api/jobs/') and path.endswith('/run'):
                job_id = int(path.split('/')[-2])
                job = DB.get_job(job_id)
                if job:
                    dry_run = data.get('dry_run', False)
                    
                    if BackupEngine.is_running():
                        self._send_json({'success': False, 'error': 'Another backup is running'}, 409)
                    else:
                        thread = threading.Thread(
                            target=BackupEngine.run_job,
                            args=(job, dry_run, False),
                            name=f"Backup-{job['name']}"
                        )
                        thread.start()
                        self._send_json({'success': True, 'message': 'Job started'})
                else:
                    self._send_json({'success': False, 'error': 'Job not found'}, 404)
            
            elif path.startswith('/api/jobs/') and path.endswith('/toggle'):
                job_id = int(path.split('/')[-2])
                enabled = int(data.get('enabled', 0))
                DB.toggle_job(job_id, enabled)
                self._send_json({'success': True, 'enabled': enabled})
            
            elif path == '/api/abort':
                BackupEngine.abort()
                self._send_json({'success': True, 'message': 'Abort requested'})
            
            elif path == '/api/settings':
                Config.C.update(data)
                success, msg = Config.save()
                self._send_json({'success': success, 'message': msg})
            
            elif path == '/api/test/wol':
                mac = data.get('mac_address')
                if mac:
                    success, msg = WakeOnLan.send_magic_packet(mac)
                    self._send_json({'success': success, 'message': msg})
                else:
                    self._send_json({'success': False, 'error': 'MAC address required'})
            
            elif path == '/api/test/ping':
                host = data.get('host')
                if host:
                    reachable = WakeOnLan.ping(host)
                    self._send_json({'success': True, 'reachable': reachable})
                else:
                    self._send_json({'success': False, 'error': 'Host required'})
            
            elif path == '/api/test/discord':
                url = Config.C.get("DISCORD_WEBHOOK_URL", "")
                if not url:
                    self._send_json({'success': False, 'error': 'Discord webhook URL not configured'})
                else:
                    success = NotifyManager.discord_notify(
                        "🧪 Test Notification",
                        "This is a test message from ATP Backup",
                        "blue"
                    )
                    self._send_json({'success': success, 'message': 'Test sent' if success else 'Failed to send'})
            
            elif path == '/api/test/mount':
                share = data.get('share')
                if share:
                    success, msg = MountManager.mount(share)
                    if success:
                        time.sleep(2)
                        MountManager.unmount(share)
                    self._send_json({'success': success, 'message': msg})
                else:
                    self._send_json({'success': False, 'error': 'Share required'})
            
            elif path == '/api/import/jobs':
                # Import jobs from JSON
                import_data = data.get('data', {})
                if import_data.get('export_type') != 'jobs':
                    self._send_json({'success': False, 'error': 'Invalid export type'}, 400)
                else:
                    jobs = import_data.get('jobs', [])
                    imported = 0
                    skipped = 0
                    for job in jobs:
                        try:
                            # Check if job with same name exists
                            existing = [j for j in DB.get_jobs() if j.get('name') == job.get('name')]
                            if existing:
                                skipped += 1
                                continue
                            DB.create_job(job)
                            imported += 1
                        except Exception as e:
                            logger.error(f"[API] Failed to import job: {e}")
                            skipped += 1
                    self._send_json({
                        'success': True,
                        'message': f'Imported {imported} jobs, skipped {skipped}',
                        'imported': imported,
                        'skipped': skipped
                    })

            elif path == '/api/import/settings':
                # Import settings from JSON
                import_data = data.get('data', {})
                if import_data.get('export_type') != 'settings':
                    self._send_json({'success': False, 'error': 'Invalid export type'}, 400)
                else:
                    settings = import_data.get('settings', {})
                    # Don't overwrite sensitive settings
                    settings.pop('DISCORD_WEBHOOK_URL', None)
                    Config.C.update(settings)
                    success, msg = Config.save()
                    self._send_json({'success': success, 'message': msg})

            # Database management endpoints
            elif path == '/api/database/clear_history':
                DB.clear_history()
                self._send_json({'success': True, 'message': 'History cleared'})
            
            elif path == '/api/database/reset_statistics':
                DB.reset_statistics()
                self._send_json({'success': True, 'message': 'Statistics reset'})
            
            elif path == '/api/database/reset':
                DB.reset_database()
                self._send_json({'success': True, 'message': 'Database reset complete'})
            
            else:
                self._send_json({'success': False, 'error': 'Not found'}, 404)
                
        except Exception as e:
            logger.error(f"[API] POST error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)
    
    def do_PUT(self):
        path = self.path
        
        try:
            data = self._read_json()
            
            if path.startswith('/api/jobs/'):
                job_id = int(path.split('/')[-1])
                job = DB.get_job(job_id)
                if job:
                    updated = {**job, **data}
                    DB.update_job(job_id, updated)
                    self._send_json({'success': True})
                else:
                    self._send_json({'success': False, 'error': 'Job not found'}, 404)
            else:
                self._send_json({'success': False, 'error': 'Not found'}, 404)
                
        except Exception as e:
            logger.error(f"[API] PUT error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)
    
    def do_DELETE(self):
        path = self.path
        
        try:
            if path.startswith('/api/jobs/'):
                job_id = int(path.split('/')[-1])
                DB.delete_job(job_id)
                self._send_json({'success': True})
            else:
                self._send_json({'success': False, 'error': 'Not found'}, 404)
                
        except Exception as e:
            logger.error(f"[API] DELETE error: {e}")
            self._send_json({'success': False, 'error': str(e)}, 500)

# ============================================
# MAIN
# ============================================

server = None
shutting_down = False

def signal_handler(signum, frame):
    global shutting_down
    if shutting_down:
        return  # Prevent re-entry
    shutting_down = True
    logger.info(f"[Main] Received signal {signum}, shutting down...")
    Scheduler.stop()
    if server:
        threading.Thread(target=server.shutdown).start()

def main():
    global server
    
    logger.info("=" * 60)
    logger.info(f"ATP Backup v{Config.VERSION} starting...")
    logger.info(f"Log level: {Config.C.get('LOG_LEVEL', 'INFO')}")
    logger.info(f"Data directory: {Config.DATA_DIR}")
    logger.info(f"Config directory: {Config.CONFIG_DIR}")
    logger.info(f"API port: {Config.C['SERVER_PORT']}")
    logger.info(f"Unassigned Devices: {'Available' if MountManager.is_ud_available() else 'Not found'}")
    logger.info(f"Retry on failure: {Config.C.get('RETRY_ON_FAILURE', True)}")
    logger.info("=" * 60)
    
    try:
        with open(Config.PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.warning(f"[Main] Could not write PID file: {e}")
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    Scheduler.start()
    
    port = Config.C['SERVER_PORT']
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), APIHandler)
        logger.info(f"[Main] API server listening on port {port}")
        server.serve_forever()
    except OSError as e:
        if e.errno == 98:
            logger.error(f"[Main] Port {port} already in use!")
        else:
            raise
    except KeyboardInterrupt:
        pass
    finally:
        Scheduler.stop()
        if os.path.exists(Config.PID_FILE):
            try:
                os.remove(Config.PID_FILE)
            except:
                pass
        logger.info("[Main] ATP Backup stopped")

if __name__ == "__main__":
    main()
