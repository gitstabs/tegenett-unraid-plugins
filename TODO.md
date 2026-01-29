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

### 1.2 Emby Smart Cache → ATP Emby Smart Cache

**Current state:** Copied as-is, has hardcoded values, manual install

**Conversion tasks:**
- [ ] Audit all hardcoded values and list them
- [ ] Create settings schema (what needs to be configurable)
- [ ] Implement settings UI for all configurable options
- [ ] Add CSRF token support (Unraid 7 requirement)
- [ ] Update to responsive design (match ATP Backup style)
- [ ] Update pluginURL to point to GitHub raw URL
- [ ] Add proper version checking
- [ ] Plugin was built to be manually installed, so it needs to be converted to a proper plugin like ATP Backup. It might be fine as is, but I'm not sure.

**Data preservation:**
- [ ] Document all data locations (config files, databases, cache)
- [ ] Create data export function (or document manual backup)
- [ ] Create data import/restore instructions
- [ ] Test upgrade path: old manual install → new GitHub install

**Hardcoded values to make configurable:**
```
(Claude skal fylle inn denne listen etter audit av koden)
- [ ] ...
- [ ] ...
```

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
- [ ] Code audit and review.

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
- [ ] Audit current code for hardcoded values
- [ ] Create configuration schema
- [ ] Implement settings UI for all configurable options
- [ ] Convert to GitHub-installable plugin
- [ ] Document data backup/restore procedure
- [ ] Code audit and review.

### 🟠 High Priority
- [ ] Match visual style with ATP Backup
- [ ] Add CSRF token support (Unraid 7 requirement)
- [ ] Modernize to responsive design

### 🟡 Medium Priority
- [ ] Improve logging and statistics
- [ ] Create proper documentation

---

## Shared Components

### 🟠 High Priority
- [ ] Extract common CSS to shared/css/tegenett-common.css
- [ ] Extract common JS utilities to shared/js/tegenett-common.js
- [ ] Create build script that injects shared code into plugins
- [ ] Document CSS class naming convention

### 🟡 Medium Priority
- [ ] Create plugin template for new plugins
- [ ] Document shared component usage

---

## Infrastructure

### 🟠 High Priority
- [ ] Set up proper build pipeline
- [ ] Create development/testing guide
- [ ] Document GitHub workflow

### 🟡 Medium Priority
- [ ] Automated version bumping
- [ ] Change log generation
- [ ] Unit tests for Python daemon

---

## Future Plugin Ideas

- [ ] ATP Docker Compose - manage multi-container stacks
- [ ] ATP UPS Monitor - advanced UPS management with graceful shutdown
- [ ] ATP Disk Health - SMART monitoring with predictions
- [ ] ATP Network Monitor - bandwidth and latency tracking

---

## Completed ✅

### atp_backup (ATP Backup)
- [x] Rename from tegenett_backup to atp_backup (2026.01.29)

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