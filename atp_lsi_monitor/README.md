<p align="center">
  <img src="../assets/icons/atp-lsi-monitor.png" alt="ATP LSI Monitor" width="96">
</p>

# ATP LSI Monitor

Monitor LSI SAS HBA cards for temperature, PHY link errors, and firmware info with configurable alerts and notifications.

**ATP** = A Tegenett Plugin

## Supported Hardware

- LSI SAS2308 / 9207-8i (tested)
- LSI SAS2008 / 9211-8i (limited - no temperature sensor)
- Other LSI MPT-based HBA cards

## Features

- **IOC Temperature Monitoring**: Real-time temperature with configurable warning/critical thresholds
- **PHY Link Errors**: Track Invalid DWord, Running Disparity, Loss of Sync, Phy Reset problems
- **Firmware Info**: Display firmware version, BIOS, chip name, board info
- **Connected Devices**: List all attached SAS/SATA drives
- **Temperature History**: SQLite database with historical data and charts
- **Multiple Notifications**: Discord, Notifiarr, Gotify, ntfy, Pushover
- **Scheduled Reports**: Daily, weekly, monthly summary reports
- **Standalone**: Includes bundled lsiutil v1.72 binary

## Requirements

- Unraid 7.0.0 or newer
- LSI SAS HBA card (MPT-based)
- Card must be in IT mode for best compatibility

## Installation

**Plugins** → **Install Plugin** → Enter:
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_lsi_monitor/atp_lsi_monitor.plg
```

## First-Time Setup

After installation:

1. Go to **Settings** → **ATP LSI Monitor**
2. The plugin will automatically detect your LSI HBA
3. Configure thresholds:
   - **Warning Temperature**: Default 50°C
   - **Critical Temperature**: Default 65°C
4. Optional: Configure notifications (Discord webhook, etc.)
5. Enable monitoring and save

## Temperature Reading

The plugin reads IOC temperature using:
```bash
lsiutil -p1 -a 25,2,0,0
```

This returns the IOC (I/O Controller) temperature from the diagnostic page.

**Note**: SAS2008-based cards (9211-8i) do NOT have a temperature sensor. Only SAS2308 and newer chips report temperature.

## PHY Link Errors

The plugin monitors these PHY error types:

| Error Type | Description |
|------------|-------------|
| Invalid DWord | Invalid data word received |
| Running Disparity | Encoding error in data stream |
| Loss of Sync | Lost synchronization with device |
| Phy Reset Problem | Issues during PHY reset |

High error counts may indicate:
- Failing cables (SFF-8087/8643)
- Poor cable quality
- Marginal drive connections
- EMI interference

## Settings Reference

| Setting | Description | Default |
|---------|-------------|---------|
| LSI_PORT | lsiutil port number (usually 1) | 1 |
| POLL_INTERVAL | How often to read temperature (seconds) | 300 |
| TEMP_WARNING | Warning threshold (°C) | 50 |
| TEMP_CRITICAL | Critical threshold (°C) | 65 |
| ALERT_ON_WARNING | Send notification on warning | Yes |
| ALERT_ON_CRITICAL | Send notification on critical | Yes |
| ALERT_ON_PHY_ERRORS | Alert when PHY errors accumulate | Yes |
| ALERT_COOLDOWN | Don't repeat same alert within (seconds) | 3600 |

## Notification Services

### Discord (Direct)
- Create a webhook in your Discord server
- Paste the webhook URL in settings

### Notifiarr
- Get API key from notifiarr.com
- Optionally specify a channel ID

### Gotify
- Self-hosted notification server
- Requires URL and application token

### ntfy
- Free notification service (ntfy.sh or self-hosted)
- Just specify a topic name

### Pushover
- Mobile push notifications
- Requires user key and API token

## Data Locations

| Path | Contents |
|------|----------|
| `/boot/config/plugins/atp_lsi_monitor/` | Settings (persistent) |
| `/mnt/user/appdata/atp_lsi_monitor/` | Database, logs |
| `/usr/local/emhttp/plugins/atp_lsi_monitor/` | Plugin files (RAM) |

## API Endpoints

The plugin exposes a local HTTP API on port 39800:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Plugin status and current temp |
| `/api/temperature` | GET | Current temperature reading |
| `/api/temperature/history` | GET | Temperature history |
| `/api/firmware` | GET | Firmware/hardware info |
| `/api/phy` | GET | PHY error counts |
| `/api/devices` | GET | Connected devices |
| `/api/health` | GET | Overall health check |
| `/api/alerts` | GET | Alert history |

## Troubleshooting

### "lsiutil not found"
The plugin includes lsiutil v1.72. If issues occur:
```bash
ls -la /usr/local/emhttp/plugins/atp_lsi_monitor/lsiutil
```

### "Cannot read temperature"
Your card may not support temperature reporting:
- SAS2008 (9211-8i): No temperature sensor
- SAS2308 (9207-8i): Has temperature sensor

### "No LSI HBA detected"
Run manually to check:
```bash
/usr/local/emhttp/plugins/atp_lsi_monitor/lsiutil -s
```

## Changelog

### v2026.01.31a
- Initial release
- IOC temperature monitoring
- PHY link error tracking
- Multiple notification services
- Scheduled reports

## Support

Issues: https://github.com/gitstabs/tegenett-unraid-plugins/issues
