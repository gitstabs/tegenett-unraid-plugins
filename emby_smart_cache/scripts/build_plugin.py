#!/usr/bin/env python3
"""
Build script for Unraid plugins.
Combines source files into a single .plg file.

Usage:
    python build_plugin.py emby_smart_cache
    python build_plugin.py emby_smart_cache --output dist/
"""

import os
import sys
import json
import argparse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent


def read_file(path: Path) -> str:
    """Read file content with UTF-8 encoding."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def build_plugin(plugin_name: str, output_dir: Path = None) -> Path:
    """Build a .plg file from plugin sources."""
    
    plugin_dir = REPO_ROOT / plugin_name
    if not plugin_dir.exists():
        raise FileNotFoundError(f"Plugin directory not found: {plugin_dir}")
    
    # Load metadata
    metadata_file = plugin_dir / "plugin" / "plugin.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
    
    with open(metadata_file) as f:
        meta = json.load(f)
    
    # Get pluginURL from metadata (REQUIRED for private repos)
    plugin_url = meta.get('pluginURL', '')
    if not plugin_url:
        print("WARNING: pluginURL not set in plugin.json - update checking won't work!")
        plugin_url = f"https://raw.githubusercontent.com/gitstabs/unraid-plugins/main/{plugin_name}/{plugin_name}.plg"
    
    # Define source files to include
    src_base = plugin_dir / "src" / "usr" / "local" / "emhttp" / "plugins" / plugin_name
    
    files = {
        'page': src_base / "EmbySmartCache.page",
        'ajax': src_base / "include" / "ajax.php",
        'python': src_base / f"{plugin_name}.py",
        'rc': src_base / f"rc.{plugin_name}",
    }
    
    # Read all source files
    content = {}
    for key, path in files.items():
        if path.exists():
            content[key] = read_file(path)
        else:
            print(f"Warning: {path} not found, skipping...")
            content[key] = ""
    
    # Build changelog
    changelog_lines = [f"##{meta['version']}"]
    for change in meta.get('changes', {}).get(meta['version'], []):
        changelog_lines.append(f"- {change}")
    changelog = "\n".join(changelog_lines)
    
    # Generate .plg content
    plg_content = f'''<?xml version='1.0' standalone='yes'?>
<!DOCTYPE PLUGIN [
<!ENTITY name      "{meta['name']}">
<!ENTITY author    "{meta['author']}">
<!ENTITY version   "{meta['version']}">
<!ENTITY launch    "{meta['launch']}">
<!ENTITY pluginURL "{plugin_url}">
]>

<PLUGIN name="&name;" author="&author;" version="&version;" launch="&launch;" pluginURL="&pluginURL;" icon="{meta['icon']}" min="{meta['min_unraid']}" support="{meta['support']}">

<CHANGES>
{changelog}
</CHANGES>

<!-- ============================================ -->
<!-- THE MAIN PAGE FILE                           -->
<!-- ============================================ -->
<FILE Name="/usr/local/emhttp/plugins/&name;/EmbySmartCache.page">
<INLINE>
<![CDATA[
{content['page']}
]]>
</INLINE>
</FILE>

<!-- ============================================ -->
<!-- AJAX HANDLER                                 -->
<!-- ============================================ -->
<FILE Name="/usr/local/emhttp/plugins/&name;/include/ajax.php">
<INLINE>
<![CDATA[
{content['ajax']}
]]>
</INLINE>
</FILE>

<!-- ============================================ -->
<!-- PYTHON DAEMON                                -->
<!-- ============================================ -->
<FILE Name="/boot/config/plugins/&name;/&name;.py" Mode="0755">
<INLINE>
<![CDATA[
{content['python']}
]]>
</INLINE>
</FILE>

<!-- ============================================ -->
<!-- RC CONTROL SCRIPT                           -->
<!-- ============================================ -->
<FILE Name="/usr/local/emhttp/plugins/&name;/rc.&name;" Mode="0755">
<INLINE>
<![CDATA[
{content['rc']}
]]>
</INLINE>
</FILE>

<!-- ============================================ -->
<!-- INSTALL SCRIPT                              -->
<!-- ============================================ -->
<FILE Run="/bin/bash" Method="install">
<INLINE>
echo "Installing Emby Smart Cache {meta['version']}..."

# Create plugin directories
mkdir -p /usr/local/emhttp/plugins/&name;/include
mkdir -p /boot/config/plugins/&name;
mkdir -p /mnt/user/appdata/emby_smart_cache/logs

# Start the service
/usr/local/emhttp/plugins/&name;/rc.&name; start

echo "Installation complete!"
</INLINE>
</FILE>

<!-- ============================================ -->
<!-- REMOVE SCRIPT                               -->
<!-- ============================================ -->
<FILE Run="/bin/bash" Method="remove">
<INLINE>
echo "Removing Emby Smart Cache..."

# Stop the service
/usr/local/emhttp/plugins/&name;/rc.&name; stop 2>/dev/null

# Remove plugin files (keep config and data)
rm -rf /usr/local/emhttp/plugins/&name;

echo "Removal complete. Config and data preserved in:"
echo "  /boot/config/plugins/&name;/"
echo "  /mnt/user/appdata/emby_smart_cache/"
</INLINE>
</FILE>

</PLUGIN>
'''
    
    # Determine output path
    if output_dir is None:
        output_dir = REPO_ROOT / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{plugin_name}.plg"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plg_content)
    
    print(f"✅ Built: {output_file}")
    print(f"   Size: {output_file.stat().st_size:,} bytes")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Build Unraid plugin .plg files")
    parser.add_argument("plugin", help="Plugin name (directory name)")
    parser.add_argument("--output", "-o", help="Output directory", default=None)
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) if args.output else None
    
    try:
        build_plugin(args.plugin, output_dir)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
