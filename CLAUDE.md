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

| Plugin | Status | Version | Description |
|--------|--------|---------|-------------|
| `atp_backup` | ✅ Active | v2026.01.30g | Backup solution with local/remote SMB, WOL, Discord notifications |
| `atp_emby_smart_cache` | ✅ Active | v2026.01.30l | Media cache management for Emby |
| Future plugins | Planned | - | TBD |

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

**Dashboard Tile Structure (Unraid 7.2+):**
```html
<span class="tile-header">
    <span class="tile-header-left">
        <i class="icon-xxx f32"></i>
        <div class="section">
            <h3 class="tile-header-main">Title</h3>
            <span>Subtitle</span>
        </div>
    </span>
    <span class="tile-header-right">
        <span class="tile-ctrl"><!-- buttons --></span>
    </span>
</span>
```

**Visual Consistency:**
- All Tegenett plugins must share the same visual language
- Primary color: `#e67e22` (orange)
- Use shared CSS from `shared/css/tegenett-common.css`
- Icons: Font Awesome 6.x

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
└── js/
    └── atp-common.js           # Shared JS utilities (ATP.ajax, formatting, etc.)
```

**Build System:**
- `build.py` - Master build script that:
  - Injects shared CSS/JS into .page files
  - Builds PLG files from src/ components
  - Validates XML and Python syntax
  - Creates version-tagged releases

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
Icon="icon-name"
Markdown="false"
---
<?php
```

⚠️ **`Markdown="false"` is MANDATORY** for pages with JavaScript!
- Without this, Unraid's Markdown parser will convert `<script>` to `<p>&lt;</p><p>script>`
- This causes JavaScript to display as text instead of executing

**Script/CSS Placement Rules:**
- External scripts (CDN like Chart.js) → In head section, BEFORE `<style>`
- Inline `<script>` → After main container is OK, but ONLY with `Markdown="false"`
- All content after the last `</div>` can be Markdown-parsed without this header

### CRITICAL: PLG ENTITY Naming Rules

**The `&name;` ENTITY is the internal plugin ID - NOT the display name!**

```xml
<!-- CORRECT -->
<!ENTITY name      "atp_backup">           <!-- snake_case, no spaces -->

<!-- WRONG - causes "checking" status stuck -->
<!ENTITY name      "ATP Backup">           <!-- spaces break everything -->
```

**Why this matters:**
- Unraid uses `&name;` as the plugin identifier in `<PLUGIN name="&name;">`
- Spaces in `&name;` cause:
  - "Checking for updates" stuck forever
  - `plugin check plugin_name` says "not installed"
  - File paths break

**Display name in Plugin List uses `displayName` ENTITY:**
```xml
<!ENTITY name        "atp_backup">           <!-- Technical ID (snake_case) -->
<!ENTITY displayName "ATP Backup">           <!-- Human-readable display name -->
```

**Display name in menu/tabs comes from the .page file:**
```
Title="ATP Backup"    <!-- This shows in Settings menu -->
```

### CRITICAL: FILE Paths in PLG

**NEVER use `&name;` ENTITY in FILE Name attributes!**

```xml
<!-- CORRECT - hardcoded paths -->
<FILE Name="/usr/local/emhttp/plugins/atp_backup/atp_backup.py" Mode="0755">

<!-- WRONG - ENTITY substitution can fail -->
<FILE Name="/usr/local/emhttp/plugins/&name;/&name;.py" Mode="0755">
```

If `&name;` contains spaces (like "ATP Backup"), the path becomes invalid.

### CRITICAL: AJAX Architecture

**Use ONE AJAX handler per plugin - NOT inline PHP in .page files!**

```
CORRECT:
.page file → UI only (HTML, CSS, JS)
ajax.php   → ALL AJAX handlers with CSRF validation

WRONG:
.page file → UI + inline PHP AJAX handler (causes confusion, dual systems)
ajax.php   → Another AJAX handler (which one is used?)
```

**Why this matters:**
- Inline PHP in .page files can conflict with Unraid's page template system
- AJAX to `/Settings/PageName` returns full HTML page, not JSON
- Separate `ajax.php` bypasses the template system and returns clean JSON

**JavaScript AJAX URL:**
```javascript
// CORRECT - goes to separate PHP file
var ajaxUrl = '/plugins/plugin_name/include/ajax.php';

// WRONG - goes through Unraid's page system, returns HTML
var ajaxUrl = '/Settings/PluginPage';
```

**CSRF Validation in ajax.php:**
```php
// Read CSRF from var.ini (not $var which is only in page context)
$var_file = '/var/local/emhttp/var.ini';
$var = @parse_ini_file($var_file);
$valid = hash_equals($var['csrf_token'], $_POST['csrf_token']);
```

### CDATA Section Rules

**Never use these inside CDATA sections (even in comments):**
- `<style>` or `</style>` as literal text
- `<script>` or `</script>` as literal text
- `]]>` sequence (closes CDATA prematurely)

```xml
<!-- WRONG - breaks parsing -->
<![CDATA[
/* This comment mentions <style> tags */
]]>

<!-- CORRECT - avoid HTML-like text in comments -->
<![CDATA[
/* This comment mentions style tags */
]]>
```

### Development Workflow

**Claude Code works directly in the GitHub repo folder (e.g., D:\Github\tegenett-unraid-plugins\)**

**Making changes:**
1. Claude edits files directly in the plugin folders
2. Claude validates PLG with `xmllint` before confirming changes
3. User reviews changes in GitHub Desktop or VS Code
4. User commits and pushes to GitHub

**Testing on Unraid:**
1. In Unraid: Plugins → Check for Updates → Update plugin
2. Or reinstall: Plugins → Install Plugin → paste raw GitHub URL

**Plugin GitHub URLs:**
```
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg
https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_emby_smart_cache/atp_emby_smart_cache.plg
```

**Quick test cycle:**
```bash
# On Unraid - force reinstall latest from GitHub
plugin install https://raw.githubusercontent.com/gitstabs/tegenett-unraid-plugins/main/atp_backup/atp_backup.plg
```

**Debugging Commands (on Unraid):**
```bash
# Check plugin status
plugin check atp_backup

# Validate PHP syntax
php -l /usr/local/emhttp/plugins/atp_backup/AtpBackup.page

# Show hidden characters (debug encoding issues)
cat -A /path/to/file | head

# Compare file sizes (detect injection issues)
wc -l /usr/local/emhttp/plugins/atp_backup/AtpBackup.page

# Check ENTITY definitions in installed PLG
head -20 /boot/config/plugins/atp_backup.plg

# Test PHP rendering directly
cd /usr/local/emhttp && php -r "
\$_SERVER['DOCUMENT_ROOT'] = '/usr/local/emhttp';
\$var = ['csrf_token' => 'test'];
include 'plugins/atp_backup/AtpBackup.page';
" | head -100
```

**Common Issues & Solutions:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Checking for updates" stuck | `&name;` has spaces | Use snake_case in ENTITY |
| JS shows as text `<p>&lt;</p>` | Missing Markdown="false" | Add to page header |
| chmod errors on install | FILE paths use `&name;` | Hardcode all paths |
| CSS/JS shows as raw text | HTML tags in CDATA comments | Remove `<style>`, `<script>` from comments |
| Plugin says "not installed" | ENTITY name mismatch | Ensure PLG filename matches `&name;` |
| AJAX returns HTML instead of JSON | Using `/Settings/Page` URL | Use `/plugins/name/include/ajax.php` |
| CSRF token invalid | Reading from wrong source | Use `parse_ini_file('/var/local/emhttp/var.ini')` in ajax.php |
| Buttons/forms do nothing | Missing AJAX handler in ajax.php | Add handler for that action |

## Reference Documentation

**Unraid Resources:**
- Security Guidelines: https://forums.unraid.net/topic/185562-security-guidelines-for-plugins/
- Responsive Migration: https://forums.unraid.net/topic/192172-responsive-webgui-plugin-migration-guide/
- Plugin Templates: https://github.com/dkaser/unraid-plugin-template

**Key Unraid Paths:**
```
/usr/local/emhttp/plugins/     # Installed plugin files (RAM)
/boot/config/plugins/          # Persistent plugin storage (USB)
/var/run/                      # PID files
/boot/config/go                # Startup script (add services here)
```

## Mandatory Validation Rules

### XML Validation (CRITICAL)
**ALWAYS validate PLG files with xmllint before delivering:**

```bash
xmllint --noout plugin_name.plg && echo "✅ XML valid!"
```

- Never claim a PLG file is ready without running this command
- If xmllint fails, fix the error before delivering
- Common issues: unescaped `<`, `>`, `&` in CDATA sections

### Python Syntax Check
```bash
python3 -m py_compile plugin_name.py
```

### Build Verification Checklist
Before delivering ANY plugin update:
1. [ ] `xmllint --noout *.plg` passes
2. [ ] Python files compile without errors
3. [ ] Version number updated in all places
4. [ ] CHANGES section updated in PLG

### Testing Checklist (for user)
After installing update on Unraid:
- [ ] CSRF token works on all forms
- [ ] Settings save and persist across reboots
- [ ] Service auto-starts after update
- [ ] Mobile responsive layout works
- [ ] Discord notifications (if applicable)
- [ ] Error handling and logging

## Communication Style

- Be concise and direct
- Show code, not just explanations
- Ask clarifying questions if requirements are unclear
- Never assume - verify with user if uncertain
- Always test changes before claiming they work
- **Never say "it's ready" without actually validating first**

## Current State

**atp_backup v2026.01.30g:**
- Features: Local/Remote SMB backup, WOL, Discord, retry logic
- Status: ✅ Fully working
- Recent fixes: Mobile responsive dashboard (cards stack vertically)
- Pending: Cloud backup (rclone integration), bandwidth scheduling

**atp_emby_smart_cache v2026.01.30l:**
- Features: Emby media caching, auto-cleanup, statistics
- Status: ✅ Fully working
- Recent fixes: Refactored to use ajax.php only (like ATP Backup), logs no auto-refresh
- Data path: `/mnt/user/appdata/atp_emby_smart_cache/`

## Known Issues & TODO

**Display Names in Plugin List:**
- Currently shows `atp_backup` instead of "ATP Backup" in Unraid Plugins page
- Need to research how other plugins achieve nice display names
- Must NOT break the "checking" status (caused by spaces in `&name;`)

**Version Bumping:**
- ALWAYS bump version on ANY change, even small fixes
- User cannot receive updates without version change
- Format: `YYYY.MM.DDx` where x is a letter (a-z) for same-day releases
