# Tegenett Backup

Smart backup solution for Unraid with local, remote SMB, Wake-on-LAN, and cloud support.

## Features

- **Local Backup**: Array to Share (rsync-based)
- **Remote SMB Backup**: Backup to Windows/NAS shares via Unassigned Devices
- **Wake-on-LAN**: Automatically wake remote hosts before backup
- **Remote Shutdown**: Shutdown Windows machines after backup (via Samba RPC)
- **Retry on Failure**: Automatically retry failed jobs with configurable intervals
- **Discord Notifications**: Rich embeds with status and statistics
- **Unraid Notifications**: Native Unraid notification support
- **Scheduling**: Hourly, daily, weekly, or custom cron schedules
- **Statistics**: Track backup history, transfer speeds, data volumes
- **Dry-run Mode**: Test backups without making changes

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB backups: [Unassigned Devices](https://forums.unraid.net/topic/92462-unassigned-devices-managing-disk-drives-and-remote-shares-outside-of-the-unraid-array/) plugin

## Installation

In Unraid, go to **Plugins** → **Install Plugin** and enter:

```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/tegenett_backup/tegenett_backup.plg
```

## Changelog

### v2026.01.28
- CRITICAL FIX: Added CSRF token support for Unraid 7 compatibility
- CRITICAL FIX: Database migration - no more manual database deletion needed
- CRITICAL FIX: Plugin files now properly update on upgrade
- BUGFIX: Changed default port to 39982 to avoid conflicts
- BUGFIX: Fixed settings save returning empty response
- BUGFIX: Fixed Discord webhook SSL issues
- BUGFIX: Fixed double-logging issue
- NEW: Retry on failure - automatically retries failed jobs
- NEW: Configurable retry interval and max attempts
- NEW: Per-job retry settings

### v2026.01.27
- Initial release

## Support

Report issues at: https://github.com/gitstabs/tegenett-unraid-plugins/issues
