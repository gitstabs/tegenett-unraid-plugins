# Emby Smart Cache

Smart caching plugin for Unraid that automatically moves actively watched media files from array storage to fast cache storage.

## Features

- 🎬 **Emby Webhook Integration** - Automatically triggered when media playback starts
- ⚡ **Smart Caching** - Moves files to fast SSD/NVMe cache during playback
- 🧹 **Automatic Cleanup** - Returns files to array after configurable delay
- 📊 **Statistics Dashboard** - Track cache operations with charts
- 🔔 **Discord Notifications** - Get alerts for cache operations
- 🔒 **Mover Ignore** - Prevents Unraid mover from moving cached files back
- 🎯 **Pre-caching** - Optionally cache next episodes in a series

## Requirements

- Unraid 7.0.0 or newer
- Emby Media Server with webhook support
- Cache drive (SSD/NVMe recommended)

## Installation

### From GitHub Releases

1. Download `emby_smart_cache.plg` from [Releases](https://github.com/gitstabs/unraid-plugins/releases)
2. Upload to your Unraid server at `/boot/config/plugins/`
3. Go to **Plugins** → **Install Plugin** → select the file

### Direct URL

```
https://github.com/gitstabs/unraid-plugins/releases/latest/download/emby_smart_cache.plg
```

## Configuration

After installation, go to **Settings** → **Emby Smart Cache** in Unraid WebGUI.

### Required Settings

| Setting | Description |
|---------|-------------|
| Emby Host | URL to your Emby server (e.g., `http://192.168.1.100:8096`) |
| Emby API Key | API key from Emby Dashboard → Advanced → API Keys |

### Path Settings

| Setting | Default | Description |
|---------|---------|-------------|
| User Share Path | `/mnt/user` | Main user share mount point |
| Cache Pool Path | `/mnt/cache_data` | Your cache pool mount point |
| Array Only Path | `/mnt/user0` | Direct array access path |

### Emby Webhook Setup

1. In Emby, go to **Dashboard** → **Webhooks**
2. Add new webhook with URL: `http://UNRAID_IP:9999/webhook`
3. Select events: **Playback Start**, **Playback Stop**

## File Structure

```
emby_smart_cache/
├── plugin/
│   ├── plugin.json          # Build metadata
│   └── plugin.j2            # PLG template
├── src/
│   ├── install/
│   │   └── slack-desc       # Package description
│   └── usr/local/emhttp/plugins/emby_smart_cache/
│       ├── EmbySmartCache.page    # WebGUI page
│       ├── emby_smart_cache.py    # Python daemon
│       ├── rc.emby_smart_cache    # Service control
│       └── include/
│           └── ajax.php           # AJAX handler
└── README.md
```

## Changelog

### v3.2.0 (2026.02.09)
- BUGFIX: Cooldown now properly waits before caching
- BUGFIX: Pre-cache next episodes now waits for cooldown first
- NEW: Configurable pre-cache episodes count (0-5)
- NEW: Rsync retry logic with exponential backoff
- NEW: Speed/time tracking for cache operations

## License

Private - All rights reserved.
