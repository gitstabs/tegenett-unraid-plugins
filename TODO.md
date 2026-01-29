# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## 🔴 PHASE 1: Plugin Restructuring (DO FIRST)

### 1.1 Uniform Naming Convention
All plugins skal hete **"ATP [Name]"** (A Tegenett Plugin) for konsistent sortering.

| Nåværende | Nytt navn | Plugin ID |
|-----------|-----------|-----------|
| tegenett_backup | ATP Backup | atp_backup |
| emby_smart_cache | ATP Emby Smart Cache | atp_emby_smart_cache |
| (future) | ATP [Name] | atp_[name] |

**Rename checklist per plugin:**
- [x] Rename folder: `tegenett_backup/` → `atp_backup/` ✅
- [x] Rename PLG file: `tegenett_backup.plg` → `atp_backup.plg` ✅
- [x] Update PLG `<!ENTITY name>` ✅
- [x] Update PLG `<!ENTITY pluginURL>` (new GitHub path) ✅
- [x] Update all internal paths in PLG (`/usr/local/emhttp/plugins/...`) ✅
- [x] Update Python daemon filename and references ✅
- [x] Update RC script filename ✅
- [x] Update PID file path ✅
- [x] Update config directory path (`/boot/config/plugins/...`) ✅
- [x] Update data directory path (`/mnt/user/appdata/...`) ✅
- [x] Update Page file `Menu=` and `Title=` ✅
- [x] Update database path references ✅
- [x] Test fresh install on Unraid ✅ Bekreftet 2026.01.29

**Post-rename instructions for user:**
1. Uninstall old plugin via Unraid GUI
2. Delete old data: `rm -rf /boot/config/plugins/old_name`
3. Install new plugin from GitHub
4. Restore data (see data migration section)

### 1.2 Emby Smart Cache → ATP Emby Smart Cache ✅ DONE

**Completed 2026.01.29:**
- [x] Renamed to atp_emby_smart_cache
- [x] Removed all personal data from defaults (API keys, IPs, paths)
- [x] Added CSRF token support (Unraid 7)
- [x] Updated colors to match ATP Backup (#e67e22)
- [x] Converted to single PLG file
- [x] Updated pluginURL to GitHub
- [x] Tested fresh install on Unraid

### 1.3 Visual Consistency (ATP Backup = Template)

All plugins must match ATP Backup's visual design:

**Design tokens (from ATP Backup):**
```css
--tb-primary: #e67e22;        /* Orange - brand color */
--tb-primary-dark: #d35400;
--tb-success: #27ae60;
--tb-danger: #c0392b;
--tb-warning: #f39c12;
--tb-info: #3498db;
```

**Required UI elements:**
- [ ] Header with plugin name, version, status badge
- [ ] Tab navigation (Dashboard, Jobs/Main, History, Statistics, Logs, Settings)
- [ ] Card-based layout with `.tb-card` class
- [ ] Consistent button styles (`.tb-btn`, `.tb-btn-primary`, etc.)
- [ ] Status badges (`.tb-badge-success`, `.tb-badge-danger`, etc.)
- [ ] Form styling (`.tb-form-group`, `.tb-checkbox-label`)
- [ ] Table styling (`.tb-table`)
- [ ] Modal dialogs (`.tb-modal`)
- [ ] Consistent color scheme and layout for same type of buttons, etc.

**For each plugin:**
- [ ] Extract common CSS to `shared/css/tegenett-common.css`
- [ ] Import shared CSS in plugin
- [ ] Replace plugin-specific colors with CSS variables
- [ ] Match layout structure with ATP Backup

---

## atp_backup (ATP Backup)

### 🔴 Critical
- [x] ~~Rename to ATP Backup (see Phase 1)~~ ✅ Done 2026.01.29
- [x] Code audit and review. ✅ Done 2026.01.30
  - CSRF validation for all modifying AJAX requests
  - Improved exception handling

### 🟠 High Priority
- [ ] Bandwidth scheduling (different limits at different times)

### 🟡 Medium Priority
- [ ] Snapshot/versioned backups (date-stamped folders)
- [ ] Export/import job configurations
- [ ] Weekly/monthly Discord summary reports
- [ ] Cloud backup support via rclone Docker container (user has not the Docker container ready yet, so we wait)
- [ ] Telegram/Pushover and slack notifications as Discord alternative

### 🟢 Nice to Have
- [ ] Web-based file browser for source/destination selection
- [ ] Backup verification (checksum comparison)
- [ ] Compression option for backups

---

## emby_smart_cache (→ ATP Emby Smart Cache)

### 🔴 Critical (see Phase 1.2 for details)
- [x] ~~Audit current code for hardcoded values~~ ✅ Done 2026.01.29
- [x] ~~Create configuration schema~~ ✅ Done 2026.01.29
- [x] ~~Implement settings UI for all configurable options~~ ✅ Done 2026.01.29
- [x] ~~Convert to GitHub-installable plugin~~ ✅ Done 2026.01.29
- [x] ~~Document data backup/restore procedure~~ ✅ Done 2026.01.29
- [x] Code audit and review. ✅ Done 2026.01.30
  - CSRF validation for all modifying AJAX requests
  - Replaced bare `except:` with specific exception types
  - Added path traversal protection in force_cleanup

### 🟠 High Priority
- [x] ~~Match visual style with ATP Backup~~ ✅ Done 2026.01.29c
- [x] ~~Add CSRF token support (Unraid 7 requirement)~~ ✅ Done 2026.01.30
- [x] ~~Modernize to responsive design~~ ✅ Done 2026.01.29b

### 🟡 Medium Priority
- [ ] Improve logging and statistics
- [ ] Create proper documentation

---

## Shared Components

### 🟠 High Priority
- [x] ~~Extract common CSS to shared/css/atp-common.css~~ Done 2026.01.30
- [x] ~~Extract common JS utilities to shared/js/atp-common.js~~ Done 2026.01.30
- [x] ~~Create build script that injects shared code into plugins~~ Done 2026.01.30 (build.py)
- [x] ~~Integrate shared CSS/JS into both plugins~~ Done 2026.01.30a
- [ ] Document CSS class naming convention
- [ ] Review plugin name references (ENTITY name vs folder names vs internal paths)
  - Note: ENTITY name = display name in Unraid GUI
  - Folder/file names use snake_case (atp_backup)
  - Internal paths must match folder names

### 🟡 Medium Priority
- [ ] Create plugin template for new plugins
- [ ] Document shared component usage

---

## Infrastructure

### 🟠 High Priority
- [x] ~~Set up proper build pipeline~~ Done 2026.01.30b (GitHub Actions)
- [x] ~~Convert ATP Backup to src-file structure~~ Done 2026.01.30b
- [ ] Create development/testing guide
- [ ] Document GitHub workflow

### 🟡 Medium Priority
- [ ] Automated version bumping
- [ ] Change log generation
- [ ] Unit tests for Python daemon

---

## Branding & Design

### 🟠 High Priority
- [ ] Design uniform Tegenett logo for all plugins
- [ ] Design plugin-specific icons (same design system as logo)
- [ ] Create icon guidelines document

### Assets
- [ ] Master Tegenett logo (SVG, PNG in multiple sizes)
- [ ] ATP Backup icon
- [ ] ATP Emby Smart Cache icon
- [ ] Favicon (existing in assets/icons/ - may need updates)

### Design System
- [ ] Color palette documentation
- [ ] Icon style guide (size, stroke width, corners)
- [ ] Badge/thumbnail specifications for Unraid plugin list

---

## Future Plugin Ideas

- [ ] ATP Docker Compose - manage multi-container stacks
- [ ] ATP UPS Monitor - advanced UPS management with graceful shutdown
- [ ] ATP Disk Health - SMART monitoring with predictions
- [ ] ATP Network Monitor - bandwidth and latency tracking

---

## Completed ✅

### atp_emby_smart_cache (ATP Emby Smart Cache)
- [x] Rename from emby_smart_cache to atp_emby_smart_cache (2026.01.29)
- [x] Removed personal data from defaults
- [x] Added CSRF token support
- [x] Updated colors to ATP theme
- [x] Tested on Unraid (2026.01.29)
- [x] **Security Audit v2026.01.30:**
  - CSRF validation for all modifying AJAX requests
  - Replaced ~20 bare `except:` with specific exception types
  - Added path traversal protection in force_cleanup
  - Better logging for exception handlers

### atp_backup (ATP Backup)
- [x] Rename from tegenett_backup to atp_backup (2026.01.29)
- [x] **Security Audit v2026.01.30:**
  - CSRF validation for all modifying AJAX requests
  - Improved exception handling

### tegenett_backup (→ ATP Backup) - Legacy
- [x] Core backup functionality (local, remote SMB)
- [x] Wake-on-LAN support
- [x] Discord notifications with embeds
- [x] Daily summary option
- [x] Auto-retry on failure
- [x] CSRF token support (Unraid 7)
- [x] Responsive UI
- [x] Job enable/disable toggle
- [x] Schedule time display and sorting
- [x] Statistics chart with proper scaling
- [x] Backup health dashboard
- [x] Reset database functions
- [x] Exclude patterns with presets
- [x] Pre/post backup scripts
- [x] Log rotation settings


### emby_smart_cache (→ ATP Emby Smart Cache)
- [x] Core functionality that works well