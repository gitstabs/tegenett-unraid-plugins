# Tegenett Plugin Icons & Branding

## Current Icons

| File | Size | Purpose |
|------|------|---------|
| `favicon.png` | 128x128 | Tegenett "T." logo (GitHub README) |
| `atp-backup.png` | 1024x1024 | ATP Backup plugin icon (Shield + T) |
| `atp-emby-smart-cache.png` | 1024x1024 | ATP Emby Smart Cache icon (Play + T) |

## Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Primary Orange** | `#F26522` | Main brand color, icons, buttons |
| **Primary Dark** | `#d35400` | Hover states |
| **Success Green** | `#27ae60` | Running status, success messages |
| **Danger Red** | `#c0392b` | Stopped status, errors |
| **Warning Yellow** | `#f39c12` | Warnings |
| **Info Blue** | `#3498db` | Information |

## Design Guidelines

- **Icon style**: Modern flat design with "T." branding element
- **Minimum size**: 32x32px (Unraid auto-scales from source)
- **Background**: Transparent (preferred) or white
- **File format**: PNG

## Usage in Plugins

Icons are downloaded from GitHub during plugin install:
```xml
<FILE Name="/usr/local/emhttp/plugins/plugin_name/icon.png">
<URL>https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/assets/icons/icon.png</URL>
</FILE>
```

Referenced in PLG and .page files:
```xml
<PLUGIN ... icon="atp-backup.png" ...>
```
```
Icon="atp-backup.png"
```
