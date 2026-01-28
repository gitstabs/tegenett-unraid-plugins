# Tegenett Backup

Smart backup solution for Unraid with local, remote SMB, Wake-on-LAN support.

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

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB backups: Unassigned Devices plugin

## Installation

**Plugins** → **Install Plugin** → Enter:
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/tegenett_backup/tegenett_backup.plg
```

## Changelog

### v2026.01.28d
- FIX: Header buttons now identical size
- FIX: PID shows correctly after service start
- FIX: All job action buttons have text labels
- NEW: Per-job backup retention (count or days)
- NEW: Granular Discord notification toggles

### v2026.01.28
- CSRF token support for Unraid 7
- Retry on failure feature

### v2026.01.27
- Initial release

## Support

https://github.com/gitstabs/tegenett-unraid-plugins/issues
