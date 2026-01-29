# ATP Backup

Smart backup solution for Unraid with local, remote SMB, Wake-on-LAN support.

**ATP** = A Tegenett Plugin

## Features

- **Local Backup**: Array to Share (rsync-based)
- **Remote SMB Backup**: Backup to Windows/NAS shares via Unassigned Devices
- **Wake-on-LAN**: Automatically wake remote hosts before backup
- **Remote Shutdown**: Shutdown Windows machines after backup
- **Backup Retention**: Per-job settings (keep X copies OR X days)
- **Retry on Failure**: Automatically retry failed jobs
- **Discord Notifications**: Granular control (start/success/failure) + daily summaries
- **Unraid Notifications**: Native notification support
- **Scheduling**: Hourly, daily, weekly, or custom cron
- **Dry-run Mode**: Test backups without changes
- **Pre/Post Scripts**: Run custom scripts before and after backups
- **Exclude Patterns**: Quick-add presets for common exclusions
- **Backup Health Dashboard**: Visual overview of job health status

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB backups: Unassigned Devices plugin

## Installation

**Plugins** → **Install Plugin** → Enter:
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg
```

## Migration from tegenett_backup

If you previously had `tegenett_backup` installed, see the migration guide below.

### Data Locations

| Old Path | New Path |
|----------|----------|
| `/boot/config/plugins/tegenett_backup/` | `/boot/config/plugins/atp_backup/` |
| `/mnt/user/appdata/tegenett_backup/` | `/mnt/user/appdata/atp_backup/` |

### Migration Steps

1. **Export your settings** (optional but recommended):
   ```bash
   cp /boot/config/plugins/tegenett_backup/settings.json /boot/config/plugins/tegenett_backup_settings_backup.json
   ```

2. **Uninstall old plugin** via Unraid GUI:
   - Plugins → Installed Plugins → tegenett_backup → Remove

3. **Clean up old startup entry**:
   ```bash
   sed -i '/tegenett_backup/d' /boot/config/go
   ```

4. **Install new plugin** via Unraid GUI:
   - Plugins → Install Plugin → paste URL above

5. **Migrate data** (if needed):
   ```bash
   # Copy config
   cp /boot/config/plugins/tegenett_backup_settings_backup.json /boot/config/plugins/atp_backup/settings.json

   # Copy database (keeps job history)
   cp /mnt/user/appdata/tegenett_backup/tegenett_backup.db /mnt/user/appdata/atp_backup/atp_backup.db
   ```

6. **Restart service**:
   ```bash
   /usr/local/emhttp/plugins/atp_backup/rc.atp_backup restart
   ```

## Changelog

### v2026.01.30
- SECURITY: Added CSRF token validation for all modifying AJAX requests
- SECURITY: Improved exception handling with specific exception types
- CODE: Better logging for all exception handlers

### v2026.01.29a
- RENAME: Plugin renamed from tegenett_backup to atp_backup
- All paths updated to use atp_backup prefix

### v2026.01.28k
- NEW: Reset Database - clear history, reset statistics, or full reset
- NEW: Exclude Patterns UI - quick-add presets
- NEW: Pre/Post Backup Scripts
- NEW: Backup Health Dashboard
- NEW: Log Rotation settings

### v2026.01.28j
- FIX: Speed now shows in appropriate units
- FIX: Improved auto-start

### v2026.01.28
- CSRF token support for Unraid 7

### v2026.01.27
- Initial release

## Support

https://github.com/gitstabs/tegenett-unraid-plugins/issues
