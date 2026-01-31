# Changelog

All notable changes to Tegenett Unraid Plugins.

---

## [2026.01.31e] - Improved Install/Remove Scripts

### Install Script Improvements
- **NEW**: Pre-install Unraid version check (requires 7.0.0+)
- **NEW**: Standardized install output format (matches Community Applications style)
- **NEW**: Remove script now cleans up PLG file from `/boot/config/plugins/`
- **IMPROVED**: Better user feedback during install/remove
- **PRESERVED**: Settings and data are kept on uninstall (user must manually delete if wanted)

---

## [2026.01.31d] - Plugin Display Names (Fixed!)

### Display Names
- **FIX**: README.md now included in PLG files for proper display in Unraid Plugins list
- Plugin description in "Installed Plugins" now shows markdown from README.md
- ATP Backup shows as "**ATP Backup**" with full description
- ATP Emby Smart Cache shows as "**ATP Emby Smart Cache**" with full description
- Technical ID (`name`) unchanged - no breaking changes to existing installations

### Technical Details
- Unraid's `ShowPlugins.php` reads `plugins/{name}/README.md` for plugin descriptions
- If README.md doesn't exist, it displays the raw plugin name (e.g., "atp_backup")
- Now build.py includes README.md in the PLG file installation

---

## [2026.01.31c] - Plugin Display Names (Attempt 1)

### Display Names
- **PARTIAL**: Added `displayName` ENTITY to PLG files
- Note: This alone didn't fix the display - README.md inclusion was needed (fixed in v2026.01.31d)

---

## [2026.01.31b] - Plugin Template & TODO Cleanup

### Plugin Template
- **NEW**: Complete plugin template in `plugin_template/`
  - `atp_template.py` - Python daemon with SQLite, HTTP API, logging
  - `AtpTemplate.page` - Web UI with tabs, modals, CRUD operations
  - `ajax.php` - AJAX handler with CSRF validation
  - `rc.atp_template` - Service control script
  - `README.md` - Usage instructions and naming conventions

### TODO Updates
- **REMOVED**: Web-based file browser (not feasible in Unraid WebGUI)
- **REMOVED**: Development guide & Unit tests (not needed for personal plugins)
- **MOVED**: Snapshot/versioned backups to Future Considerations
- **MOVED**: Alternative notifications to Future Considerations with privacy comparison table

---

## [2026.01.31a] - ATP Backup Major Features

### Bandwidth Scheduling
- **NEW**: Two bandwidth profiles (Night/Day) with configurable start times
- Profile A: Typically unlimited (night hours, e.g., 22:00-06:00)
- Profile B: Typically limited (day hours, e.g., 06:00-22:00)
- Jobs can override with their own bandwidth limit

### Export / Import
- **NEW**: Export jobs to JSON file (passwords excluded for security)
- **NEW**: Export settings to JSON file (webhook excluded for security)
- **NEW**: Import previously exported configurations
- Allows easy migration between Unraid systems

### Discord Summary Reports
- **NEW**: Weekly summary reports (configurable day and hour)
- **NEW**: Monthly summary reports (configurable day and hour)
- Shows total jobs, success rate, data transferred, duration

### Checksum Verification
- **NEW**: Per-job option to use rsync `--checksum` flag
- More accurate file comparison (detects corruption)
- Slower but recommended for critical data

### Database Schema
- Migration to v4: Added `verify_checksum` column to jobs table

---

## [2026.01.31] - Build System & Documentation

### Build System
- **NEW**: `--bump` flag in build.py for automatic version bumping
  - `python build.py --bump` - bump all plugins
  - `python build.py --bump backup` - bump specific plugin
  - Handles YYYY.MM.DDx format (increments letter on same day)

### Documentation
- **NEW**: `shared/README.md` - CSS class naming convention guide
- **UPDATE**: TODO.md - marked completed tasks

---

## [2026.01.30l] - ATP Emby Smart Cache
- **FIX**: Logs tab no longer auto-refreshes (easier to copy text)

## [2026.01.30k] - ATP Emby Smart Cache
- **FIX**: CSRF validation fallback for $_REQUEST

## [2026.01.30j] - ATP Emby Smart Cache
- **REFACTOR**: Removed inline PHP AJAX handler, uses ajax.php only

## [2026.01.30h] - ATP Emby Smart Cache
- **FIX**: CSRF error resolved - AJAX now routes to correct handler

## [2026.01.30g] - ATP Backup
- **FIX**: Dashboard cards stack vertically on tablet/mobile

## [2026.01.30f] - ATP Backup
- **FIX**: Recent Activity scrollbar stays within card on mobile

## [2026.01.30e/f] - Build System & Bug Fixes
- **FIX**: ENTITY name must be snake_case (spaces caused "checking" stuck)
- **FIX**: `Markdown="false"` required for JS to work
- **NEW**: Shared CSS/JS build system
- **NEW**: GitHub Actions workflow

## [2026.01.30] - Security Audit
- **SECURITY**: CSRF validation for all modifying AJAX requests
- **SECURITY**: Improved exception handling
- **SECURITY**: Path traversal protection

## [2026.01.29] - Plugin Renaming
- **RENAME**: `tegenett_backup` → `atp_backup`
- **RENAME**: `emby_smart_cache` → `atp_emby_smart_cache`
- **UI**: Responsive design, visual consistency
