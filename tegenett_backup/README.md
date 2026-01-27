# Tegenett Backup

Smart backup solution for Unraid with local, remote SMB, Wake-on-LAN, and cloud support.

## Features

- **Local Backup**: Array to Share (rsync-based)
- **Remote SMB Backup**: Backup to Windows/NAS shares via Unassigned Devices
- **Wake-on-LAN**: Automatically wake remote hosts before backup
- **Remote Shutdown**: Shutdown Windows machines after backup (via Samba RPC)
- **Discord Notifications**: Rich embeds with status and statistics
- **Unraid Notifications**: Native Unraid notification support
- **Scheduling**: Hourly, daily, weekly, or custom cron schedules
- **Statistics**: Track backup history, transfer speeds, data volumes
- **Dry-run Mode**: Test backups without making changes

## Requirements

- Unraid 7.0.0 or newer
- For remote SMB backups: [Unassigned Devices](https://forums.unraid.net/topic/92462-unassigned-devices-managing-disk-drives-and-remote-shares-outside-of-the-unraid-array/) plugin

## Installation

### From Plugin URL (Recommended)

1. In Unraid, go to **Plugins** → **Install Plugin**
2. Enter URL: `https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/tegenett_backup/tegenett_backup.plg`
3. Click **Install**

### Manual Installation

1. Download `tegenett_backup.plg`
2. Copy to `/boot/config/plugins/tegenett_backup/`
3. Install via Unraid GUI or run: `installplg /boot/config/plugins/tegenett_backup/tegenett_backup.plg`

## Configuration

### Adding a Backup Job

1. Go to **Settings** → **Tegenett Backup**
2. Click **Add Job**
3. Configure:
   - **Name**: Descriptive name for the job
   - **Type**: Local, Remote SMB, or Remote SMB with WOL
   - **Source Path**: Path to backup (e.g., `/mnt/user/appdata`)
   - **Destination**: Where to store backup
   - **Schedule**: When to run automatically

### Wake-on-LAN Setup

For remote hosts that need to be woken:

1. Select job type: **Remote SMB with WOL**
2. Enter the remote host's MAC address
3. Optionally enable **Shutdown after backup**

### Windows Shutdown Requirements

To allow Unraid to shutdown a Windows machine after backup:

1. On Windows, run `regedit`
2. Navigate to: `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System`
3. Create DWORD: `LocalAccountTokenFilterPolicy` = `1`
4. In Windows Firewall, enable: "Remote Service Management (NP-In)"

### Discord Webhook

1. In Discord, go to Server Settings → Integrations → Webhooks
2. Create a new webhook and copy the URL
3. Paste into Tegenett Backup settings

## Data Locations

- **Database & Logs**: `/mnt/user/appdata/tegenett_backup/`
- **Configuration**: `/boot/config/plugins/tegenett_backup/settings.json`

## API

The plugin exposes a REST API on port 9998:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Service status |
| `/api/jobs` | GET/POST | List/create jobs |
| `/api/jobs/{id}` | GET/PUT/DELETE | Job operations |
| `/api/jobs/{id}/run` | POST | Run job |
| `/api/history` | GET | Backup history |
| `/api/stats` | GET | Statistics |
| `/api/logs` | GET | Service logs |
| `/api/settings` | GET/POST | Configuration |

## Troubleshooting

### Service won't start

Check the log file:
```bash
cat /mnt/user/appdata/tegenett_backup/logs/tegenett_backup.log
```

### Remote backup fails

1. Verify Unassigned Devices is installed
2. Check that the remote share is configured in UD
3. Test mounting manually: `rc.unassigned mount "//host/share"`

### WOL doesn't wake host

1. Verify MAC address format (AA:BB:CC:DD:EE:FF)
2. Ensure WOL is enabled in BIOS/UEFI
3. Check network allows broadcast packets

## License

MIT License - see LICENSE file

## Support

Report issues at: https://github.com/gitstabs/tegenett-unraid-plugins/issues
