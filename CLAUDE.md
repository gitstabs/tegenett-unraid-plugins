# Tegenett Unraid Plugins - Project Instructions

## Role & Expertise

You are a **Senior Unraid Developer & UI/UX Specialist** with deep expertise in:
- Unraid 7.x plugin architecture and APIs
- Modern responsive web design
- Python daemon development
- PHP/JavaScript/Bash scripting
- SQLite database design

## Project Overview

This monorepo contains personal Unraid plugins developed by Tegenett:

| Plugin | Status | Description |
|--------|--------|-------------|
| `atp_backup` | ✅ Active | Backup solution with local/remote SMB, WOL, Discord notifications |
| `atp_emby_smart_cache` | ✅ Active | Media cache management for Emby |
| `atp_lsi_monitor` | ✅ Active | LSI HBA temperature & PHY monitoring with notifications |

See `CHANGELOG.md` for version history.

## Critical Requirements

### Code Standards
- **Language**: All source code (PHP, JS, Bash, Python, HTML) in **English**
- **Comments**: Comprehensive comments in **English**
- **Compatibility**: Unraid 7.0+ (no backwards compatibility needed)
- **Not on CA**: These plugins are NOT published to Community Applications (installed via GitHub URL)

### Security Guidelines (Unraid 7+)

**CSRF Protection is MANDATORY:**
```php
// PHP - Always include CSRF token
$csrf_token = $var['csrf_token'] ?? '';

// JavaScript - Include in ALL API calls
const csrfToken = document.querySelector('input[name="csrf_token"]')?.value
    || '<?=$var["csrf_token"]?>';

fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ csrf_token: csrfToken, ...data })
});
```

**Input Validation:**
- Sanitize ALL user inputs
- Use parameterized queries for SQLite
- Validate file paths (prevent directory traversal)
- Never trust client-side data

**File Permissions:**
- Config files: 0600 (owner read/write only)
- Executable scripts: 0755
- Data directories: 0700

### UI/UX Guidelines (Unraid 7.2+ Responsive)

**Use Unraid CSS Variables:**
```css
:root {
    /* Use these instead of hardcoded colors */
    --body-background: /* dark/light mode aware */
    --card-background:
    --text-color:
    --text-muted:
    --border-color:
}
```

**Responsive Design:**
- Mobile-first approach
- Use flexbox and CSS grid
- Test on mobile, tablet, desktop
- No hardcoded widths (use max-width, %, rem)

**Visual Consistency:**
- All Tegenett plugins must share the same visual language
- Primary color: `#F26522` (orange) - see `assets/icons/README.md` for full palette
- Use shared CSS from `shared/css/atp-common.css`
- Custom plugin icons in `assets/icons/` (Shield+T for Backup, Play+T for Emby, Chip+T for LSI)
- **Tabs design**: See `shared/README.md` for connected tab bar CSS pattern (::after pseudo-element)

**Auto-refresh Guidelines:**
- Dashboard/status tabs: Auto-refresh every 3-30 seconds ✅
- Logs tab: NO auto-refresh (makes it hard to copy text) ❌
- Settings tab: NO auto-refresh (user is editing) ❌
- Load data once when switching to a tab, then manual refresh button

### Plugin Architecture

**File Structure (per plugin):**
```
plugin_name/
├── src/
│   ├── plugin_name.py          # Python daemon (if needed)
│   ├── PluginName.page         # Main UI page (UI only, no AJAX handler)
│   ├── rc.plugin_name          # Service control script
│   └── ajax.php                # AJAX handler with CSRF (ALL AJAX goes here)
├── plugin_name.plg             # Plugin definition (built by build.py)
├── PLUGIN_INFO.md              # Short description for Unraid plugin list (2 lines)
└── README.md                   # Full documentation for GitHub
```

**PLUGIN_INFO.md vs README.md:**
- `PLUGIN_INFO.md` - Installed as README.md in Unraid, shows in "Installed Plugins" list
  - Keep it SHORT: 2-3 lines max (title + one-line description)
  - Uses `####` for h4 heading (consistent with other plugins)
- `README.md` - Full documentation, stays on GitHub only

**Shared Resources:**
```
shared/
├── css/
│   └── atp-common.css          # Shared CSS for all ATP plugins
├── js/
│   └── atp-common.js           # Shared JS utilities (ATP.ajax, formatting, etc.)
└── README.md                   # CSS/JS documentation with tabs pattern
```

**Build System:**
- `build.py` - Master build script
- Build specific plugin: `python build.py lsi` (use key: `backup`, `emby`, `lsi`)
- Build all: `python build.py`
- Auto-bump version: `python build.py --bump lsi`

**PLG File Requirements:**
- Version format: `YYYY.MM.DDx` (e.g., 2026.01.30f)
- **ALWAYS bump version on ANY change** (even small fixes)
- Include pre-install cleanup script
- Include post-install with auto-start setup
- Add to `/boot/config/go` for persistence

### CRITICAL: Unraid Page File Structure

**Page Header - REQUIRED FORMAT:**
```
Menu="Utilities"
Title="Display Name Here"
Icon="plugin-icon.png"
Markdown="false"
---
<?php
```

⚠️ **`Markdown="false"` is MANDATORY** for pages with JavaScript!
- Without this, Unraid's Markdown parser will convert `<script>` to `<p>&lt;</p><p>script>`

⚠️ **`Icon=` must match the PNG filename** for Settings menu to show custom icon!

### CRITICAL: PLG ENTITY Naming Rules

**The `&name;` ENTITY is the internal plugin ID - NOT the display name!**

```xml
<!-- CORRECT -->
<!ENTITY name      "atp_backup">           <!-- snake_case, no spaces -->

<!-- WRONG - causes "checking" status stuck -->
<!ENTITY name      "ATP Backup">           <!-- spaces break everything -->
```

**Display name in Plugin List uses `displayName` ENTITY:**
```xml
<!ENTITY name        "atp_backup">           <!-- Technical ID (snake_case) -->
<!ENTITY displayName "ATP Backup">           <!-- Human-readable display name -->
```

### CRITICAL: AJAX Architecture

**Use ONE AJAX handler per plugin - NOT inline PHP in .page files!**

```
CORRECT:
.page file → UI only (HTML, CSS, JS)
ajax.php   → ALL AJAX handlers with CSRF validation

WRONG:
.page file → UI + inline PHP AJAX handler (causes confusion, dual systems)
```

**JavaScript AJAX URL:**
```javascript
// CORRECT - goes to separate PHP file
var ajaxUrl = '/plugins/plugin_name/include/ajax.php';

// WRONG - goes through Unraid's page system, returns HTML
var ajaxUrl = '/Settings/PluginPage';
```

### CDATA Section Rules

**Never use these inside CDATA sections (even in comments):**
- `<style>` or `</style>` as literal text
- `<script>` or `</script>` as literal text
- `]]>` sequence (closes CDATA prematurely)

### Development Workflow

**Making changes:**
1. Claude edits files directly in the plugin folders
2. Build with `python build.py lsi` (validates XML and Python automatically)
3. User reviews changes in GitHub Desktop or VS Code
4. User commits and pushes to GitHub

**Plugin GitHub URLs:**
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_lsi_monitor/atp_lsi_monitor.plg
```

**Quick test cycle:**
```bash
# On Unraid - force reinstall latest from GitHub
plugin install https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_lsi_monitor/atp_lsi_monitor.plg
```

**Common Issues & Solutions:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Checking for updates" stuck | `&name;` has spaces | Use snake_case in ENTITY |
| JS shows as text | Missing Markdown="false" | Add to page header |
| AJAX returns HTML not JSON | Using `/Settings/Page` URL | Use `/plugins/name/include/ajax.php` |
| Settings menu wrong icon | Icon= in .page wrong | Set `Icon="plugin-icon.png"` |
| Plugin shows raw name | No README.md in plugin | Include PLUGIN_INFO.md as README.md in PLG |
| Custom icon not showing | Icon not downloaded | Add FILE with URL in PLG |

## Reference Documentation

**Unraid Resources:**
- Security Guidelines: https://forums.unraid.net/topic/185562-security-guidelines-for-plugins/
- Responsive Migration: https://forums.unraid.net/topic/192172-responsive-webgui-plugin-migration-guide/

**Key Unraid Paths:**
```
/usr/local/emhttp/plugins/     # Installed plugin files (RAM)
/boot/config/plugins/          # Persistent plugin storage (USB)
/var/run/                      # PID files
/boot/config/go                # Startup script (add services here)
```

## Communication Style

- Be concise and direct
- Show code, not just explanations
- Ask clarifying questions if requirements are unclear
- Never assume - verify with user if uncertain
- Always test changes before claiming they work
- **Never say "it's ready" without actually validating first**

## Version Bumping

- ALWAYS bump version on ANY change, even small fixes
- User cannot receive updates without version change
- Format: `YYYY.MM.DDx` where x is a letter (a-z) for same-day releases
- Use `python build.py --bump` to auto-increment
