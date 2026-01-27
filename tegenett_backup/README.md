# Tegenett Backup

Smart backup solution for Unraid with local, remote SMB, Wake-on-LAN, and cloud support.

## Features

- **Local Backup**: Array to Share (rsync-based)
- **Remote SMB Backup**: Backup to Windows/NAS shares via Unassigned Devices
- **Wake-on-LAN**: Automatically wake remote hosts before backup
- **Remote Shutdown**: Shutdown Windows machines after backup (via Samba RPC)
- **Retry on Failure**: Automatically retry failed jobs
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

### v2026.01.27a
- BUGFIX: Changed default port to 39982 to avoid conflicts
- BUGFIX: Fixed double-logging issue
- BUGFIX: Fixed settings save returning empty response
- BUGFIX: Fixed Discord webhook SSL issues
- NEW: Retry on failure - automatically retries failed jobs
- NEW: Configurable retry interval and max attempts

### v2026.01.27
- Initial release

## Support

Report issues at: https://github.com/gitstabs/tegenett-unraid-plugins/issues
