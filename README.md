<p align="center">
  <img src="assets/icons/favicon.png" alt="Tegenett Logo" width="128">
</p>

# Tegenett Unraid Plugins

Personal Unraid 7.x plugins by Tegenett. **ATP** = A Tegenett Plugin.

## Available Plugins

| Plugin | Icon | Description | Status |
|--------|:----:|-------------|--------|
| [ATP Backup](atp_backup/) | <img src="assets/icons/atp-backup.png" width="32"> | Smart backup with local/remote SMB, WOL, Discord notifications | ✅ Active |
| [ATP Emby Smart Cache](atp_emby_smart_cache/) | <img src="assets/icons/atp-emby-smart-cache.png" width="32"> | Intelligent media caching for Emby | ✅ Active |
| [ATP LSI Monitor](atp_lsi_monitor/) | <img src="assets/icons/atp-lsi-monitor.png" width="32"> | LSI HBA temperature & PHY monitoring with notifications | ✅ Active |

## Installation

In Unraid: **Plugins** → **Install Plugin** → paste URL:

### ATP Backup
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg
```

**Features:**
- Local and remote SMB backups (rsync-based)
- Wake-on-LAN with auto-shutdown
- Discord notifications (start/success/failure + daily summary)
- Retry on failure
- Pre/post backup scripts
- Backup health dashboard

### ATP Emby Smart Cache
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg
```

**Features:**
- Automatic caching of actively watched media to SSD/NVMe
- Pre-cache next episodes for seamless binge-watching
- Bandwidth limiting and space management
- Discord notifications
- SQLite state tracking

### ATP LSI Monitor
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_lsi_monitor/atp_lsi_monitor.plg
```

**Features:**
- IOC temperature monitoring for LSI SAS HBA cards (SAS2308, 9207-8i, etc.)
- PHY link error tracking (Invalid DWord, Running Disparity, Loss of Sync)
- Firmware and hardware info display
- Multiple notification services: Discord, Notifiarr, Gotify, ntfy, Pushover
- Temperature history with charts
- Scheduled reports (daily/weekly/monthly)
- Bundled lsiutil v1.72 binary (standalone)

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB backups: Unassigned Devices plugin
- For Emby Smart Cache: Emby Media Server with API access
- For LSI Monitor: LSI SAS HBA card (SAS2308/9207-8i recommended for temperature)

## Support

Issues: https://github.com/gitstabs/tegenett-unraid-plugins/issues

## License

These plugins are provided as-is for personal use.
