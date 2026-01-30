#!/usr/bin/env python3
"""
ATP Plugin Build System - v2026.01.30
Master build script for all ATP (A Tegenett Plugin) plugins

Usage:
    python build.py              # Build all plugins
    python build.py backup       # Build only atp_backup
    python build.py emby         # Build only atp_emby_smart_cache
    python build.py --validate   # Validate without building
    python build.py --bump       # Bump version (YYYY.MM.DD format)

Features:
- Builds PLG files from source components
- Injects shared CSS/JS automatically
- Validates XML structure
- Validates Python syntax
- Reports file sizes
"""

import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Project root
ROOT = Path(__file__).parent

# Shared resources
SHARED_CSS = ROOT / 'shared' / 'css' / 'atp-common.css'
SHARED_JS = ROOT / 'shared' / 'js' / 'atp-common.js'

# Plugin definitions
PLUGINS = {
    'backup': {
        'name': 'atp_backup',
        'display_name': 'ATP Backup',
        'dir': ROOT / 'atp_backup',
        'has_build_script': True,  # Uses existing build logic in PLG
    },
    'emby': {
        'name': 'atp_emby_smart_cache',
        'display_name': 'ATP Emby Smart Cache',
        'dir': ROOT / 'atp_emby_smart_cache',
        'has_build_script': True,
    }
}


def read_file(path: Path) -> str:
    """Read file content with UTF-8 encoding."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(path: Path, content: str):
    """Write file content with UTF-8 encoding and Unix line endings."""
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)


def get_shared_css() -> str:
    """Get shared CSS content."""
    if SHARED_CSS.exists():
        return read_file(SHARED_CSS)
    return ''


def get_shared_js() -> str:
    """Get shared JS content."""
    if SHARED_JS.exists():
        return read_file(SHARED_JS)
    return ''


def validate_xml(plg_path: Path) -> bool:
    """Validate PLG file XML structure."""
    try:
        import xml.etree.ElementTree as ET
        with open(plg_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # PLG files have DOCTYPE that ElementTree can't parse directly
        # Remove XML declaration, DOCTYPE and entities for validation
        content_clean = re.sub(r'<\?xml[^?]+\?>', '', content)
        content_clean = re.sub(r'<!DOCTYPE[^>]+\]>', '', content_clean, flags=re.DOTALL)
        content_clean = re.sub(r'&\w+;', 'ENTITY', content_clean)
        content_clean = content_clean.strip()

        ET.fromstring(content_clean)
        return True
    except Exception as e:
        print(f"  XML Error: {e}")
        return False


def validate_python(py_path: Path) -> bool:
    """Validate Python syntax."""
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', str(py_path)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  Python Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"  Python validation failed: {e}")
        return False


def inject_shared_resources(page_content: str, prefix: str = 'esc') -> str:
    """
    Inject shared CSS/JS into a .page file.
    The shared CSS already defines --atp-* variables.
    We add aliases so plugin-specific --{prefix}-* also work.
    """
    shared_css = get_shared_css()
    shared_js = get_shared_js()

    if not shared_css and not shared_js:
        return page_content

    # Shared CSS is injected first (it defines --atp-* variables)
    # Then we add aliases for backwards compatibility with plugin-specific prefixes
    css_injection = f"""
/* ============================================
   ATP SHARED CSS - Injected by build.py
   ============================================ */
{shared_css}

/* Backwards compatibility aliases: --{prefix}-* maps to --atp-* */
:root {{
    --{prefix}-primary: var(--atp-primary);
    --{prefix}-primary-dark: var(--atp-primary-dark);
    --{prefix}-success: var(--atp-success);
    --{prefix}-danger: var(--atp-danger);
    --{prefix}-warning: var(--atp-warning);
    --{prefix}-info: var(--atp-info);
    --{prefix}-bg: var(--atp-bg);
    --{prefix}-card-bg: var(--atp-card-bg);
    --{prefix}-text: var(--atp-text);
    --{prefix}-text-muted: var(--atp-text-muted);
    --{prefix}-border: var(--atp-border);
}}
"""

    # Find the <style> tag and inject shared CSS at the beginning
    style_match = re.search(r'(<style[^>]*>)', page_content)
    if style_match:
        insert_pos = style_match.end()
        page_content = page_content[:insert_pos] + '\n' + css_injection + '\n' + page_content[insert_pos:]

    # Inject shared JS before closing </script> tag (at the end)
    if shared_js:
        js_injection = f"""
/* ============================================
   ATP SHARED JS - Injected by build.py
   ============================================ */
{shared_js}
"""
        # Find the last </script> and inject before it
        last_script_end = page_content.rfind('</script>')
        if last_script_end != -1:
            page_content = page_content[:last_script_end] + '\n' + js_injection + '\n' + page_content[last_script_end:]

    return page_content


def build_atp_emby_smart_cache() -> bool:
    """Build ATP Emby Smart Cache plugin."""
    plugin = PLUGINS['emby']
    src_dir = plugin['dir'] / 'src'
    output = plugin['dir'] / 'atp_emby_smart_cache.plg'

    print(f"\nBuilding {plugin['display_name']}...")

    # Read source files
    try:
        page_content = read_file(src_dir / 'AtpEmbySmartCache.page')
        python_content = read_file(src_dir / 'atp_emby_smart_cache.py')
        rc_content = read_file(src_dir / 'rc.atp_emby_smart_cache')
        ajax_content = read_file(src_dir / 'ajax.php')
    except FileNotFoundError as e:
        print(f"  Error: Missing source file - {e}")
        return False

    # Inject shared CSS/JS into page content
    page_content = inject_shared_resources(page_content, prefix='esc')
    print("  Injected shared CSS/JS")

    # Get version from page content
    version_match = re.search(r'\$version\s*=\s*["\']v?(\d{4}\.\d{2}\.\d{2}\w*)["\']', page_content)
    version = version_match.group(1) if version_match else datetime.now().strftime('%Y.%m.%d')

    plg = f'''<?xml version='1.0' standalone='yes'?>
<!DOCTYPE PLUGIN [
<!ENTITY name      "atp_emby_smart_cache">
<!ENTITY author    "Tegenett">
<!ENTITY version   "{version}">
<!ENTITY launch    "Settings/AtpEmbySmartCache">
<!ENTITY pluginURL "https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg">
]>

<PLUGIN name="&name;" author="&author;" version="&version;" launch="&launch;" pluginURL="&pluginURL;" icon="bolt" min="7.0.0" support="https://github.com/gitstabs/tegenett-unraid-plugins/issues">

<CHANGES>
##2026.01.30h
- FIX: AJAX URL changed from ajax.php to page URL (inline PHP handler doesn't require CSRF)

##2026.01.30g
- FIX: CSRF token now sent with all modifying AJAX requests (save, cleanup, service control, etc.)
- FIX: Logs tab now auto-refreshes like other tabs

##2026.01.30f
- FIX: Added Markdown="false" to page header to prevent Unraid from parsing script as Markdown

##2026.01.30e
- FIX: Moved Chart.js script to head section (fixes JS showing as text after container)

##2026.01.30d
- FIX: ENTITY name restored to snake_case (atp_emby_smart_cache) for Unraid plugin ID

##2026.01.30c
- FIX: FILE paths now use hardcoded snake_case (atp_emby_smart_cache) instead of ENTITY name

##2026.01.30b
- FIX: Removed HTML tags from shared CSS/JS comments that broke page rendering

##2026.01.30a
- BUILD: Shared CSS/JS now injected automatically from shared/ folder
- BUILD: CSS variable aliases for backwards compatibility (--esc-* maps to --atp-*)

##2026.01.30
- SECURITY: Added CSRF token validation for all modifying AJAX requests
- SECURITY: Improved exception handling with specific exception types
- SECURITY: Added path traversal protection in force_cleanup
- CODE: Better logging for all exception handlers

##2026.01.29e
- FIX: Logs panel styling restored (esc-log-viewer class)

##2026.01.29d
- UI: Added PID display in Running status badge
- UI: Added Start/Stop button in header (consistent with ATP Backup)
- FIX: Service control via AJAX (start/stop)

##2026.01.29c
- UI: Complete visual overhaul to match ATP Backup design system
- UI: New card-based Settings layout with organized sections
- UI: Square status badges (consistent with ATP Backup)
- UI: Header without orange underline, version moved to badge area
- UI: Stat cards with centered icons matching ATP Backup style
- UI: Form hints added for all settings fields

##2026.01.29b
- UI: Responsive tables - all tables now support horizontal scrolling on mobile
- UI: ESC-style tabs - active tab fully highlighted for better visibility
- UI: Dashboard status colors - Running/Stopped clearly colored (green/red)
- UI: Mobile responsive improvements for tablets and phones

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
<FILE Name="/usr/local/emhttp/plugins/atp_emby_smart_cache/AtpEmbySmartCache.page">
<INLINE>
<![CDATA[
{page_content}
]]>
</INLINE>
</FILE>

<!-- Python Daemon -->
<FILE Name="/usr/local/emhttp/plugins/atp_emby_smart_cache/atp_emby_smart_cache.py" Mode="0755">
<INLINE>
<![CDATA[
{python_content}
]]>
</INLINE>
</FILE>

<!-- RC Service Script -->
<FILE Name="/usr/local/emhttp/plugins/atp_emby_smart_cache/rc.atp_emby_smart_cache" Mode="0755">
<INLINE>
<![CDATA[
{rc_content}
]]>
</INLINE>
</FILE>

<!-- AJAX Handler -->
<FILE Name="/usr/local/emhttp/plugins/atp_emby_smart_cache/include/ajax.php">
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
echo "ATP Emby Smart Cache v{version} installed!"
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

    write_file(output, plg)

    # Validate
    xml_valid = validate_xml(output)
    py_valid = validate_python(src_dir / 'atp_emby_smart_cache.py')

    size = output.stat().st_size
    print(f"  Output: {output}")
    print(f"  Size: {size:,} bytes")
    print(f"  XML valid: {'Yes' if xml_valid else 'NO'}")
    print(f"  Python valid: {'Yes' if py_valid else 'NO'}")

    return xml_valid and py_valid


def build_atp_backup() -> bool:
    """Build ATP Backup plugin from src files."""
    plugin = PLUGINS['backup']
    src_dir = plugin['dir'] / 'src'
    output = plugin['dir'] / 'atp_backup.plg'

    print(f"\nBuilding {plugin['display_name']}...")

    # Read source files
    try:
        page_content = read_file(src_dir / 'AtpBackup.page')
        python_content = read_file(src_dir / 'atp_backup.py')
        rc_content = read_file(src_dir / 'rc.atp_backup')
        ajax_content = read_file(src_dir / 'ajax.php')
    except FileNotFoundError as e:
        print(f"  Error: Missing source file - {e}")
        return False

    # Inject shared CSS/JS into page content
    page_content = inject_shared_resources(page_content, prefix='tb')
    print("  Injected shared CSS/JS")

    # Get version from page content
    version_match = re.search(r'\$version\s*=\s*["\']v?(\d{4}\.\d{2}\.\d{2}\w*)["\']', page_content)
    version = version_match.group(1) if version_match else datetime.now().strftime('%Y.%m.%d')

    plg = f'''<?xml version='1.0' standalone='yes'?>
<!DOCTYPE PLUGIN [
<!ENTITY name      "atp_backup">
<!ENTITY author    "Tegenett">
<!ENTITY version   "{version}">
<!ENTITY launch    "Settings/AtpBackup">
<!ENTITY pluginURL "https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg">
]>

<PLUGIN name="&name;" author="&author;" version="&version;" launch="&launch;" pluginURL="&pluginURL;" icon="shield" min="7.0.0" support="https://github.com/gitstabs/tegenett-unraid-plugins/issues">

<CHANGES>
##2026.01.30g
- FIX: Dashboard cards (Upcoming Jobs, Recent Activity) now stack vertically on tablet/mobile
- FIX: Improved responsive layout for smaller screens

##2026.01.30f
- FIX: Recent Activity table scrollbar now stays within card on mobile/tablet

##2026.01.30e
- FIX: ENTITY name restored to snake_case (atp_backup) for Unraid plugin ID

##2026.01.30d
- BUILD: Rebuild with fixed build system

##2026.01.30c
- FIX: Removed HTML tags from shared CSS/JS comments that broke page rendering

##2026.01.30b
- BUILD: Converted to src-file structure for automatic GitHub builds
- BUILD: Shared CSS/JS now injected automatically from shared/ folder

##2026.01.30a
- BUILD: Shared CSS/JS now injected automatically from shared/ folder
- BUILD: CSS variable aliases for backwards compatibility (--tb-* maps to --atp-*)

##2026.01.30
- SECURITY: Added CSRF token validation for all modifying AJAX requests
- SECURITY: Improved exception handling with specific exception types
- CODE: PHP handler now validates Unraid 7.x CSRF tokens

##2026.01.29d
- UI: Tab buttons margin/font reset for consistent spacing (reversion bump)

##2026.01.29c
- UI: Version moved to far right (consistent with ATP Emby Smart Cache)
- UI: Tab buttons reset margin for consistent gap spacing

##2026.01.29b
- UI: New tab styling (full button highlight instead of underline)
- UI: Improved mobile responsiveness for all tables
- UI: Better table headers with uppercase styling

##2026.01.29a
- RENAME: Plugin renamed from tegenett_backup to atp_backup (A Tegenett Plugin)
- All paths updated: config, data, logs now use atp_backup prefix
- NOTE: Requires fresh install - see migration guide

##2026.01.28k
- NEW: Reset Database - clear history, reset statistics, or full reset
- NEW: Exclude Patterns UI - quick-add presets (temp, logs, cache, OS junk, docker)
- NEW: Pre/Post Backup Scripts - run custom scripts before and after backups
- NEW: Backup Health Dashboard - visual overview of job health status
- NEW: Log Rotation - automatic rotation with configurable size and count
- FIX: Database schema v3 for pre/post scripts

##2026.01.28j
- FIX: Speed now shows in appropriate units (B/s, KB/s, MB/s)
- FIX: Size and speed formatting in Discord notifications
- FIX: Improved auto-start with delayed background start

##2026.01.28i
- FIX: Rsync stats parsing

##2026.01.28h
- FIX: Service auto-starts via /boot/config/go

##2026.01.28
- CSRF token support for Unraid 7

##2026.01.27
- Initial release
</CHANGES>

<!-- Pre-install: Stop existing service and clean up -->
<FILE Run="/bin/bash">
<INLINE>
<![CDATA[
#!/bin/bash
PLUGIN_NAME="atp_backup"
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

rm -rf "${{PLUGIN_DIR}}"
mkdir -p "${{PLUGIN_DIR}}/include"

echo "$(date): Pre-install complete" >> "$LOG"
]]>
</INLINE>
</FILE>

<!-- Main Page File -->
<FILE Name="/usr/local/emhttp/plugins/atp_backup/AtpBackup.page">
<INLINE>
<![CDATA[
{page_content}
]]>
</INLINE>
</FILE>

<!-- Python Daemon -->
<FILE Name="/usr/local/emhttp/plugins/atp_backup/atp_backup.py" Mode="0755">
<INLINE>
<![CDATA[
{python_content}
]]>
</INLINE>
</FILE>

<!-- RC Service Script -->
<FILE Name="/usr/local/emhttp/plugins/atp_backup/rc.atp_backup" Mode="0755">
<INLINE>
<![CDATA[
{rc_content}
]]>
</INLINE>
</FILE>

<!-- AJAX Handler -->
<FILE Name="/usr/local/emhttp/plugins/atp_backup/include/ajax.php">
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
PLUGIN_NAME="atp_backup"
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
    echo "# Start ATP Backup" >> "$GO_FILE"
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
echo "ATP Backup v{version} installed!"
echo "Service will start in 5 seconds..."
]]>
</INLINE>
</FILE>

<!-- Uninstall script -->
<FILE Run="/bin/bash" Method="remove">
<INLINE>
<![CDATA[
#!/bin/bash
PLUGIN_NAME="atp_backup"
RC_SCRIPT="/usr/local/emhttp/plugins/${{PLUGIN_NAME}}/rc.${{PLUGIN_NAME}}"
GO_FILE="/boot/config/go"

echo "Removing ATP Backup..."

# Stop service
if [ -f "$RC_SCRIPT" ]; then
    "$RC_SCRIPT" stop 2>/dev/null
fi
pkill -f "${{PLUGIN_NAME}}.py" 2>/dev/null || true
rm -f "/var/run/${{PLUGIN_NAME}}.pid"

# Remove from startup
if [ -f "$GO_FILE" ]; then
    sed -i "/# Start ATP Backup/d" "$GO_FILE"
    sed -i "/rc.${{PLUGIN_NAME}}/d" "$GO_FILE"
fi

# Remove plugin files (keep config and data)
rm -rf "/usr/local/emhttp/plugins/${{PLUGIN_NAME}}"
rm -f "/var/log/${{PLUGIN_NAME}}_install.log"
rm -f "/var/log/${{PLUGIN_NAME}}_startup.log"

echo "ATP Backup removed."
echo "Config preserved at: /boot/config/plugins/${{PLUGIN_NAME}}"
echo "Data preserved at: /mnt/user/appdata/${{PLUGIN_NAME}}"
]]>
</INLINE>
</FILE>

</PLUGIN>
'''

    write_file(output, plg)

    # Validate
    xml_valid = validate_xml(output)
    py_valid = validate_python(src_dir / 'atp_backup.py')

    size = output.stat().st_size
    print(f"  Output: {output}")
    print(f"  Size: {size:,} bytes")
    print(f"  XML valid: {'Yes' if xml_valid else 'NO'}")
    print(f"  Python valid: {'Yes' if py_valid else 'NO'}")

    return xml_valid and py_valid


def print_shared_info():
    """Print information about shared resources."""
    print("\n" + "=" * 50)
    print("SHARED RESOURCES")
    print("=" * 50)

    if SHARED_CSS.exists():
        size = SHARED_CSS.stat().st_size
        print(f"  CSS: {SHARED_CSS} ({size:,} bytes)")
    else:
        print(f"  CSS: Not found at {SHARED_CSS}")

    if SHARED_JS.exists():
        size = SHARED_JS.stat().st_size
        print(f"  JS:  {SHARED_JS} ({size:,} bytes)")
    else:
        print(f"  JS:  Not found at {SHARED_JS}")


def main():
    print("=" * 50)
    print("ATP PLUGIN BUILD SYSTEM")
    print("=" * 50)

    args = sys.argv[1:]

    # Determine what to build
    build_all = len(args) == 0 or '--all' in args
    build_backup = build_all or 'backup' in args
    build_emby = build_all or 'emby' in args
    validate_only = '--validate' in args

    # Print shared resources info
    print_shared_info()

    # Build/validate plugins
    results = {}

    if build_backup:
        results['backup'] = build_atp_backup()

    if build_emby:
        results['emby'] = build_atp_emby_smart_cache()

    # Summary
    print("\n" + "=" * 50)
    print("BUILD SUMMARY")
    print("=" * 50)

    all_success = True
    for name, success in results.items():
        status = "OK" if success else "FAILED"
        plugin_name = PLUGINS[name]['display_name']
        print(f"  {plugin_name}: {status}")
        if not success:
            all_success = False

    if all_success:
        print("\nAll builds successful!")
        return 0
    else:
        print("\nSome builds failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
