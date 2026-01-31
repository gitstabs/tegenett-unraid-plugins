# ATP Plugin Template

This is a starter template for creating new ATP (A Tegenett Plugin) plugins for Unraid.

## Quick Start

1. **Copy the template:**
   ```bash
   cp -r plugin_template atp_new_plugin
   ```

2. **Rename files (replace `atp_template` with your plugin name):**
   ```bash
   cd atp_new_plugin
   mv src/atp_template.py src/atp_new_plugin.py
   mv src/AtpTemplate.page src/AtpNewPlugin.page
   mv src/rc.atp_template src/rc.atp_new_plugin
   ```

3. **Search and replace in all files:**
   - `atp_template` → `atp_new_plugin` (snake_case)
   - `AtpTemplate` → `AtpNewPlugin` (PascalCase)
   - `ATP Template` → `ATP New Plugin` (Display name)
   - `39999` → Your unique port number

4. **Update the .plg file:**
   - Change version number
   - Update description
   - Add any dependencies

5. **Build:**
   ```bash
   python build.py atp_new_plugin
   ```

## File Structure

```
atp_new_plugin/
├── src/
│   ├── atp_new_plugin.py      # Python daemon (API server)
│   ├── AtpNewPlugin.page      # Web UI (HTML/CSS/JS)
│   ├── ajax.php               # AJAX handler (PHP → Python API proxy)
│   └── rc.atp_new_plugin      # Service control script (start/stop)
├── atp_new_plugin.plg         # Plugin definition (auto-built)
└── README.md
```

## Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Plugin ID | `atp_snake_case` | `atp_backup` |
| Display Name | Title Case | `ATP Backup` |
| Page File | `AtpPascalCase.page` | `AtpBackup.page` |
| Python File | `atp_snake_case.py` | `atp_backup.py` |
| RC Script | `rc.atp_snake_case` | `rc.atp_backup` |
| CSS Classes | `atp-kebab-case` | `.atp-card` |
| Plugin-specific CSS | `xx-kebab-case` | `.tb-job-card` |

## Port Allocation

Each plugin needs a unique port. Current allocations:
- `39982` - ATP Backup
- `39983` - ATP Emby Smart Cache
- `39999` - Template (change this!)

## Key Paths on Unraid

| Path | Purpose |
|------|---------|
| `/usr/local/emhttp/plugins/PLUGIN/` | Installed files (RAM) |
| `/boot/config/plugins/PLUGIN/` | Persistent config (USB) |
| `/mnt/user/appdata/PLUGIN/` | Data directory |
| `/var/run/PLUGIN.pid` | PID file |

## Development Workflow

1. Edit files in this repo
2. Run `python build.py plugin_name` to build .plg
3. Push to GitHub
4. On Unraid: Plugins → Install Plugin → paste raw GitHub URL

## Testing Checklist

- [ ] Service starts without errors
- [ ] Web UI loads correctly
- [ ] CSRF token works on all forms
- [ ] Settings save and persist
- [ ] Mobile responsive layout
- [ ] Service auto-starts after reboot
