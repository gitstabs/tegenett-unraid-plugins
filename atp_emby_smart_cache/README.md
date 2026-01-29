# ATP Emby Smart Cache

Intelligent media caching for Emby - automatically moves actively watched content to fast storage (SSD/NVMe cache).

**ATP** = A Tegenett Plugin

## How It Works

1. Monitors Emby playback sessions via API
2. When you start watching a movie/episode, it copies the file to your cache drive
3. Creates a symlink so Emby continues to see the file in its original location
4. Automatically cleans up cached files after a configurable delay
5. Pre-caches next episodes in a series for seamless binge-watching

## Features

- **Smart Caching**: Only caches files you're actively watching
- **Pre-cache Episodes**: Automatically cache next episodes in a series
- **Cooldown Timers**: Configurable delays before caching (prevents false triggers)
- **Bandwidth Limiting**: Control rsync speed to avoid saturating your network
- **Space Management**: Automatically cleans up when cache is full
- **Discord Notifications**: Get notified about cache operations
- **Retry Logic**: Automatic retries with exponential backoff for failed operations
- **SQLite State**: Robust state tracking that survives reboots

## Requirements

- Unraid 7.0.0 or newer
- Emby Media Server with API access
- A cache drive (SSD/NVMe recommended)
- Docker path mapping configured (if Emby runs in Docker)

## Installation

**Plugins** → **Install Plugin** → Enter:
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg
```

## First-Time Setup

After installation, you **MUST** configure these settings:

1. Go to **Settings** → **ATP Emby Smart Cache**
2. Configure required settings:
   - **Emby Host**: `http://YOUR_EMBY_IP:8096`
   - **Emby API Key**: Get from Emby Dashboard → API Keys
   - **Cache Path**: Your SSD/NVMe cache mount (e.g., `/mnt/cache`)
3. Optional but recommended:
   - **Docker Path Map**: If Emby runs in Docker (e.g., `/data/media:/mnt/user/data/media`)
   - **Discord Webhook**: For notifications
4. Enable the plugin
5. Save settings

## Migration from emby_smart_cache

If you previously had `emby_smart_cache` installed:

### Data Locations

| Old Path | New Path |
|----------|----------|
| `/boot/config/plugins/emby_smart_cache/` | `/boot/config/plugins/atp_emby_smart_cache/` |
| `/mnt/user/appdata/emby_smart_cache/` | `/mnt/user/appdata/atp_emby_smart_cache/` |

### Migration Steps

1. **Stop and note your current settings** (take a screenshot)

2. **Uninstall old plugin** via Unraid GUI

3. **Clean up old startup entry**:
   ```bash
   sed -i '/emby_smart_cache/d' /boot/config/go
   ```

4. **Install new plugin** (URL above)

5. **Re-enter your settings** in the new plugin

6. **Optionally migrate database** (keeps history):
   ```bash
   cp /mnt/user/appdata/emby_smart_cache/state.db /mnt/user/appdata/atp_emby_smart_cache/state.db
   ```

## Settings Reference

| Setting | Description | Default |
|---------|-------------|---------|
| EMBY_HOST | Emby server URL | (empty - must configure) |
| EMBY_API_KEY | API key from Emby | (empty - must configure) |
| CACHE_PATH | Where to cache files | /mnt/cache |
| DOCKER_PATH_MAP | Docker path translation | (empty) |
| MIN_FREE_SPACE_GB | Minimum free space on cache | 100 GB |
| CLEANUP_DELAY_HOURS | How long to keep cached files | 24 hours |
| COOLDOWN_MOVIE_SEC | Wait before caching movies | 60 seconds |
| COOLDOWN_EPISODE_SEC | Wait before caching episodes | 30 seconds |
| PRECACHE_EPISODES | Number of next episodes to cache | 1 |
| RSYNC_BWLIMIT | Bandwidth limit (KB/s, 0=unlimited) | 0 |

## Changelog

### v2026.01.30
- SECURITY: Added CSRF token validation for all modifying AJAX requests
- SECURITY: Improved exception handling with specific exception types (replaced bare `except:` blocks)
- SECURITY: Added path traversal protection in force_cleanup
- CODE: Better logging for all exception handlers

### v2026.01.29e
- FIX: Logs panel styling restored (esc-log-viewer class)

### v2026.01.29d
- UI: Added PID display in Running status badge
- UI: Added Start/Stop button in header (consistent with ATP Backup)
- FIX: Service control via AJAX (start/stop)

### v2026.01.29c
- UI: Complete visual overhaul to match ATP Backup design system
- UI: New card-based Settings layout with organized sections
- UI: Square status badges (consistent with ATP Backup)
- UI: Header without orange underline, version moved to badge area
- UI: Stat cards with centered icons matching ATP Backup style

### v2026.01.29b
- UI: Responsive tables - all tables now support horizontal scrolling on mobile
- UI: ESC-style tabs - active tab fully highlighted for better visibility
- UI: Dashboard status colors - Running/Stopped clearly colored (green/red)
- UI: Mobile responsive improvements for tablets and phones

### v2026.01.29a
- RENAME: Plugin renamed from emby_smart_cache to atp_emby_smart_cache
- SECURITY: All personal data removed from defaults
- SECURITY: CSRF token support for Unraid 7
- UI: Colors updated to match ATP Backup theme

### v2026.02.09.1 (as emby_smart_cache)
- Cooldown fixes
- Pre-cache improvements
- Rsync retry logic
- Speed/time tracking

## Support

Issues: https://github.com/gitstabs/tegenett-unraid-plugins/issues
