# Tegenett Unraid Plugins

Personal Unraid 7.x plugins by Tegenett. **ATP** = A Tegenett Plugin.

## Available Plugins

| Plugin | Description | Status |
|--------|-------------|--------|
| [ATP Backup](atp_backup/) | Smart backup with local/remote SMB, WOL, Discord notifications | ✅ Active |
| [ATP Emby Smart Cache](emby_smart_cache/) | Intelligent media caching for Emby | 🔧 In development |

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

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB: Unassigned Devices plugin

## Support

Issues: https://github.com/gitstabs/tegenett-unraid-plugins/issues

## License

These plugins are provided as-is for personal use.
