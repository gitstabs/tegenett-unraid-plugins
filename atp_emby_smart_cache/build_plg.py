#!/usr/bin/env python3
"""
Build script for ATP Emby Smart Cache PLG file
Combines all source files into a single installable PLG
"""
import os

SRC_DIR = os.path.join(os.path.dirname(__file__), 'src')
OUTPUT = os.path.join(os.path.dirname(__file__), 'atp_emby_smart_cache.plg')

def read_file(filename):
    path = os.path.join(SRC_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def build_plg():
    page_content = read_file('AtpEmbySmartCache.page')
    python_content = read_file('atp_emby_smart_cache.py')
    rc_content = read_file('rc.atp_emby_smart_cache')
    ajax_content = read_file('ajax.php')

    plg = f'''<?xml version='1.0' standalone='yes'?>
<!DOCTYPE PLUGIN [
<!ENTITY name      "atp_emby_smart_cache">
<!ENTITY author    "Tegenett">
<!ENTITY version   "2026.01.29a">
<!ENTITY launch    "Settings/AtpEmbySmartCache">
<!ENTITY pluginURL "https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg">
]>

<PLUGIN name="&name;" author="&author;" version="&version;" launch="&launch;" pluginURL="&pluginURL;" icon="bolt" min="7.0.0" support="https://github.com/gitstabs/tegenett-unraid-plugins/issues">

<CHANGES>
##2026.01.29a
- RENAME: Plugin renamed from emby_smart_cache to atp_emby_smart_cache (A Tegenett Plugin)
- SECURITY: All personal data removed from defaults (user must configure)
- SECURITY: CSRF token support added for Unraid 7
- UI: Colors updated to match ATP Backup theme (#e67e22)
- All paths updated to use atp_emby_smart_cache prefix
- NOTE: Requires fresh install - see migration guide

##2026.02.09.1 (previous version as emby_smart_cache)
- BUGFIX: Cooldown now properly waits before caching
- BUGFIX: Pre-cache next episodes now waits for cooldown first
- NEW: Configurable pre-cache episodes count (0-5)
- NEW: Rsync retry logic with exponential backoff
- NEW: Speed/time tracking for cache operations
</CHANGES>

<!-- Pre-install: Stop existing service and clean up -->
<FILE Run="/bin/bash">
<INLINE>
<![CDATA[
#!/bin/bash
PLUGIN_NAME="atp_emby_smart_cache"
PLUGIN_DIR="/usr/local/emhttp/plugins/${{PLUGIN_NAME}}"
LOG="/var/log/${{PLUGIN_NAME}}_install.log"

echo "$(date): Pre-install starting" >> "$LOG"

# Stop old service if running
if [ -f "/var/run/${{PLUGIN_NAME}}.pid" ]; then
    PID=$(cat /var/run/${{PLUGIN_NAME}}.pid)
    echo "$(date): Stopping service PID $PID" >> "$LOG"
    kill "$PID" 2>/dev/null
    sleep 3
fi
pkill -f "${{PLUGIN_NAME}}.py" 2>/dev/null || true

# Also stop old emby_smart_cache if migrating
pkill -f "emby_smart_cache.py" 2>/dev/null || true

rm -rf "${{PLUGIN_DIR}}"
mkdir -p "${{PLUGIN_DIR}}/include"

echo "$(date): Pre-install complete" >> "$LOG"
]]>
</INLINE>
</FILE>

<!-- Main Page File -->
<FILE Name="/usr/local/emhttp/plugins/&name;/AtpEmbySmartCache.page">
<INLINE>
<![CDATA[
{page_content}
]]>
</INLINE>
</FILE>

<!-- Python Daemon -->
<FILE Name="/usr/local/emhttp/plugins/&name;/&name;.py" Mode="0755">
<INLINE>
<![CDATA[
{python_content}
]]>
</INLINE>
</FILE>

<!-- RC Service Script -->
<FILE Name="/usr/local/emhttp/plugins/&name;/rc.&name;" Mode="0755">
<INLINE>
<![CDATA[
{rc_content}
]]>
</INLINE>
</FILE>

<!-- AJAX Handler -->
<FILE Name="/usr/local/emhttp/plugins/&name;/include/ajax.php">
<INLINE>
<![CDATA[
{ajax_content}
]]>
</INLINE>
</FILE>

<!-- Post-install: Set up directories and auto-start -->
<FILE Run="/bin/bash">
<INLINE>
<![CDATA[
#!/bin/bash
PLUGIN_NAME="atp_emby_smart_cache"
DATA_DIR="/mnt/user/appdata/${{PLUGIN_NAME}}"
CONFIG_DIR="/boot/config/plugins/${{PLUGIN_NAME}}"
RC_SCRIPT="/usr/local/emhttp/plugins/${{PLUGIN_NAME}}/rc.${{PLUGIN_NAME}}"
GO_FILE="/boot/config/go"
LOG="/var/log/${{PLUGIN_NAME}}_install.log"

echo "$(date): Post-install starting" >> "$LOG"

# Create directories
mkdir -p "$DATA_DIR/logs"
mkdir -p "$CONFIG_DIR"

# Make scripts executable
chmod +x "/usr/local/emhttp/plugins/${{PLUGIN_NAME}}/${{PLUGIN_NAME}}.py"
chmod +x "$RC_SCRIPT"

# Add to startup if not already there
if ! grep -q "rc.${{PLUGIN_NAME}}" "$GO_FILE" 2>/dev/null; then
    echo "" >> "$GO_FILE"
    echo "# Start ATP Emby Smart Cache" >> "$GO_FILE"
    echo "$RC_SCRIPT start &" >> "$GO_FILE"
    echo "$(date): Added to $GO_FILE" >> "$LOG"
fi

# Start the service in background with delay
(
    sleep 5
    "$RC_SCRIPT" start >> "$LOG" 2>&1
) &

echo "$(date): Post-install complete" >> "$LOG"
echo ""
echo "ATP Emby Smart Cache v2026.01.29a installed!"
echo "Service will start in 5 seconds..."
echo ""
echo "IMPORTANT: Configure settings before enabling:"
echo "  - Emby Host URL"
echo "  - Emby API Key"
echo "  - Cache Path"
]]>
</INLINE>
</FILE>

<!-- Uninstall script -->
<FILE Run="/bin/bash" Method="remove">
<INLINE>
<![CDATA[
#!/bin/bash
PLUGIN_NAME="atp_emby_smart_cache"
RC_SCRIPT="/usr/local/emhttp/plugins/${{PLUGIN_NAME}}/rc.${{PLUGIN_NAME}}"
GO_FILE="/boot/config/go"

echo "Removing ATP Emby Smart Cache..."

# Stop service
if [ -f "$RC_SCRIPT" ]; then
    "$RC_SCRIPT" stop 2>/dev/null
fi
pkill -f "${{PLUGIN_NAME}}.py" 2>/dev/null || true
rm -f "/var/run/${{PLUGIN_NAME}}.pid"

# Remove from startup
if [ -f "$GO_FILE" ]; then
    sed -i "/# Start ATP Emby Smart Cache/d" "$GO_FILE"
    sed -i "/rc.${{PLUGIN_NAME}}/d" "$GO_FILE"
fi

# Remove plugin files (keep config and data)
rm -rf "/usr/local/emhttp/plugins/${{PLUGIN_NAME}}"
rm -f "/var/log/${{PLUGIN_NAME}}_install.log"
rm -f "/var/log/${{PLUGIN_NAME}}_startup.log"

echo "ATP Emby Smart Cache removed."
echo "Config preserved at: /boot/config/plugins/${{PLUGIN_NAME}}"
echo "Data preserved at: /mnt/user/appdata/${{PLUGIN_NAME}}"
]]>
</INLINE>
</FILE>

</PLUGIN>
'''

    with open(OUTPUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(plg)

    print(f"Built: {OUTPUT}")
    print(f"Size: {os.path.getsize(OUTPUT):,} bytes")

if __name__ == '__main__':
    build_plg()
