# Unraid 7.x Plugin Development Guidelines

## Overview

This document captures best practices for developing Unraid 7.x plugins, compiled from official documentation and community resources.

## Plugin File Structure

### PLG File (Plugin Definition)

```xml
<?xml version='1.0' standalone='yes'?>
<!DOCTYPE PLUGIN [
<!ENTITY name      "plugin_name">
<!ENTITY author    "Your Name">
<!ENTITY version   "2026.01.28a">
<!ENTITY launch    "Settings/PluginPage">
<!ENTITY pluginURL "https://raw.githubusercontent.com/user/repo/main/plugin.plg">
]>

<PLUGIN name="&name;" author="&author;" version="&version;" 
        launch="&launch;" pluginURL="&pluginURL;" 
        icon="shield" min="7.0.0">

<CHANGES>
##2026.01.28a
- Initial release
</CHANGES>

<!-- Pre-install cleanup -->
<FILE Run="/bin/bash">
<INLINE>
<![CDATA[
#!/bin/bash
# Stop existing service, clean up old files
]]>
</INLINE>
</FILE>

<!-- Plugin files -->
<FILE Name="/usr/local/emhttp/plugins/&name;/PluginPage.page">
<INLINE>
<![CDATA[
<!-- Page content -->
]]>
</INLINE>
</FILE>

<!-- Post-install setup -->
<FILE Run="/bin/bash">
<INLINE>
<![CDATA[
#!/bin/bash
# Create directories, set permissions, start service
# Add to /boot/config/go for auto-start on boot
]]>
</INLINE>
</FILE>

<!-- Remove script -->
<FILE Run="/bin/bash" Method="remove">
<INLINE>
<![CDATA[
#!/bin/bash
# Stop service, remove files, clean up /boot/config/go
]]>
</INLINE>
</FILE>

</PLUGIN>
```

## Security Requirements (Unraid 7+)

### CSRF Token Validation

**Every form submission and AJAX POST must include CSRF token:**

```php
<?php
// Get CSRF token from Unraid
$csrf_token = $var['csrf_token'] ?? '';
?>
<script>var csrf_token = "<?=$csrf_token?>";</script>
```

```javascript
// Include in all AJAX calls
async function apiPost(action, data = {}) {
    const response = await fetch('/plugins/plugin_name/include/ajax.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            action: action,
            csrf_token: csrf_token,
            ...data
        })
    });
    return response.json();
}
```

```php
// ajax.php - Validate CSRF token
<?php
$docroot = $docroot ?? $_SERVER['DOCUMENT_ROOT'] ?: '/usr/local/emhttp';
require_once "$docroot/webGui/include/Wrappers.php";

// Validate CSRF token for POST requests
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $csrf = $_POST['csrf_token'] ?? '';
    if (!isset($var['csrf_token']) || $csrf !== $var['csrf_token']) {
        echo json_encode(['success' => false, 'error' => 'Invalid CSRF token']);
        exit;
    }
}
```

### Input Sanitization

```php
// Always sanitize user input
$value = htmlspecialchars($_POST['value'] ?? '', ENT_QUOTES, 'UTF-8');
$path = realpath($_POST['path'] ?? '');

// Validate paths
if (strpos($path, '/mnt/user/') !== 0) {
    die('Invalid path');
}
```

## UI/UX Guidelines (Unraid 7.2+)

### Responsive Design

Unraid 7.2 introduced responsive design. Plugins must follow these guidelines:

```css
/* Use CSS variables for theme compatibility */
:root {
    --plugin-primary: #e67e22;
}

.plugin-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

/* Mobile-first responsive grid */
.plugin-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 20px;
}

@media (min-width: 768px) {
    .plugin-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (min-width: 1200px) {
    .plugin-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}
```

### Dashboard Tiles (Unraid 7.2+)

```html
<tbody>
    <tr>
        <td>
            <span class="tile-header">
                <span class="tile-header-left">
                    <i class="icon-performance f32"></i>
                    <div class="section">
                        <h3 class="tile-header-main">Tile Title</h3>
                        <span>Subtitle</span>
                    </div>
                </span>
                <span class="tile-header-right">
                    <span class="tile-ctrl">
                        <button>Action</button>
                    </span>
                </span>
            </span>
        </td>
    </tr>
    <tr>
        <td>
            <!-- Tile content -->
        </td>
    </tr>
</tbody>
```

### Removed/Changed Classes

| Old (6.x) | New (7.2+) |
|-----------|------------|
| `.ctrl` | `.tile-ctrl` within `.tile-header-right` |
| `span.ctrl` with float | Removed, use flexbox |
| Hardcoded widths | Use responsive units (%, rem, vw) |
| `gap: 20px` | `gap: 2rem` |

## Service Management

### RC Script Template

```bash
#!/bin/bash
# rc.plugin_name - Service control script

PLUGIN_NAME="plugin_name"
DAEMON="/usr/local/emhttp/plugins/${PLUGIN_NAME}/${PLUGIN_NAME}.py"
PID_FILE="/var/run/${PLUGIN_NAME}.pid"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "${PLUGIN_NAME} is already running"
        return 1
    fi
    
    echo "Starting ${PLUGIN_NAME}..."
    nohup python3 "$DAEMON" >/dev/null 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    
    if kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "${PLUGIN_NAME} started (PID $(cat $PID_FILE))"
    else
        echo "Failed to start ${PLUGIN_NAME}"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "Stopping ${PLUGIN_NAME}..."
        kill "$PID" 2>/dev/null
        sleep 2
        kill -0 "$PID" 2>/dev/null && kill -9 "$PID"
        rm -f "$PID_FILE"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) stop; sleep 1; start ;;
    status) [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null && echo "Running" || echo "Stopped" ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac
```

### Auto-start on Boot

Add to `/boot/config/go` during post-install:

```bash
GO_FILE="/boot/config/go"
RC_SCRIPT="/usr/local/emhttp/plugins/${PLUGIN_NAME}/rc.${PLUGIN_NAME}"

if ! grep -q "rc.${PLUGIN_NAME}" "${GO_FILE}"; then
    echo "" >> "${GO_FILE}"
    echo "# Start ${PLUGIN_NAME}" >> "${GO_FILE}"
    echo "${RC_SCRIPT} start &" >> "${GO_FILE}"
fi
```

## Notifications

### Unraid Built-in

```bash
/usr/local/emhttp/webGui/scripts/notify \
    -i normal \
    -s "Plugin Name" \
    -d "Notification message" \
    -m "Detailed message"
```

### Discord Webhook

```python
import requests

def send_discord(webhook_url, title, description, color="green"):
    colors = {"green": 0x27ae60, "red": 0xc0392b, "orange": 0xe67e22}
    
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": colors.get(color, 0x3498db)
        }]
    }
    
    requests.post(webhook_url, json=payload, timeout=10)
```

## Data Storage

### Paths

| Purpose | Path | Persistence |
|---------|------|-------------|
| Plugin files | `/usr/local/emhttp/plugins/name/` | RAM (rebuilt on boot) |
| Config | `/boot/config/plugins/name/` | Flash drive (persistent) |
| Data/Logs | `/mnt/user/appdata/name/` | Array (persistent) |
| PID files | `/var/run/` | RAM |

### SQLite Database

```python
import sqlite3

DB_PATH = "/mnt/user/appdata/plugin_name/database.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Use parameterized queries to prevent SQL injection
def get_job(job_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE id = ?", 
            (job_id,)
        ).fetchone()
```

## Testing Checklist

- [ ] CSRF token included in all forms/AJAX
- [ ] Input validation on all user data
- [ ] Responsive on mobile/tablet/desktop
- [ ] Service starts after plugin install
- [ ] Service starts after Unraid reboot
- [ ] Settings persist after reboot
- [ ] Proper error handling and logging
- [ ] Clean uninstall (no orphaned files)

## Resources

- [Unraid Forums - Programming](https://forums.unraid.net/forum/57-programming/)
- [Security Guidelines](https://forums.unraid.net/topic/185562-security-guidelines-for-plugins/)
- [Responsive WebGUI Migration](https://forums.unraid.net/topic/192172-responsive-webgui-plugin-migration-guide/)
- [Plugin Template](https://github.com/dkaser/unraid-plugin-template)
