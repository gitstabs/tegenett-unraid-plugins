# Changelog

All notable changes to Tegenett Unraid Plugins will be documented in this file.

## [2026.01.30] - Major Build System Overhaul

### ATP Backup v2026.01.30e
- **FIX**: ENTITY name restored to snake_case (`atp_backup`) for Unraid plugin ID
- **FIX**: Synchronized version numbers across PLG, .page, and .py files
- **BUILD**: Now built from src/ files via build.py

### ATP Emby Smart Cache v2026.01.30f
- **FIX**: Added `Markdown="false"` to page header - fixes JS showing as text
- **FIX**: Moved Chart.js script to head section
- **FIX**: ENTITY name restored to snake_case (`atp_emby_smart_cache`)
- **FIX**: FILE paths now use hardcoded paths instead of `&name;` ENTITY
- **FIX**: Removed HTML tags from shared CSS/JS comments that broke CDATA parsing
- **BUILD**: Now built from src/ files via build.py

### Shared Components (NEW)
- **NEW**: `shared/css/atp-common.css` - Common styles for all ATP plugins
- **NEW**: `shared/js/atp-common.js` - Common JS utilities (ATP.ajax, formatting, etc.)
- **NEW**: `build.py` - Master build script that injects shared code and builds PLG files
- **NEW**: GitHub Actions workflow for automatic builds on push

### Critical Bug Fixes Discovered
| Issue | Cause | Fix |
|-------|-------|-----|
| "Checking for updates" stuck | `&name;` ENTITY had spaces | Use snake_case only |
| JS shows as `<p>&lt;</p>` text | Unraid Markdown parser | Add `Markdown="false"` to header |
| chmod errors on install | FILE paths used `&name;` | Hardcode all paths |
| CSS/JS shows as raw text | HTML tags in CDATA comments | Avoid `<style>`, `<script>` in comments |

---

## [2026.01.30] - Security Audit

### ATP Backup
- **SECURITY**: CSRF token validation for all modifying AJAX requests
- **SECURITY**: Improved exception handling with specific exception types

### ATP Emby Smart Cache
- **SECURITY**: CSRF token validation for all modifying AJAX requests
- **SECURITY**: Replaced ~20 bare `except:` with specific exception types
- **SECURITY**: Added path traversal protection in force_cleanup
- **SECURITY**: Better logging for exception handlers

---

## [2026.01.29] - Plugin Renaming & Restructuring

### ATP Backup (formerly tegenett_backup)
- **RENAME**: `tegenett_backup` → `atp_backup`
- All internal paths updated
- Plugin ID: `atp_backup`

### ATP Emby Smart Cache (formerly emby_smart_cache)
- **RENAME**: `emby_smart_cache` → `atp_emby_smart_cache`
- **SECURITY**: Removed all personal data from defaults (API keys, IPs, paths)
- **SECURITY**: Added CSRF token support for Unraid 7
- **UI**: Updated colors to ATP theme (#e67e22 orange)
- **UI**: Responsive design improvements
- **UI**: Visual consistency with ATP Backup
- Plugin ID: `atp_emby_smart_cache`

---

## Pre-2026.01.29 (Legacy)

### tegenett_backup
- Core backup functionality (local, remote SMB)
- Wake-on-LAN support
- Discord notifications with embeds
- Daily summary option
- Auto-retry on failure
- Responsive UI
- Statistics dashboard
- Backup health monitoring

### emby_smart_cache
- Core media caching functionality
- Pre-cache next episodes
- Bandwidth limiting
- Space management
- SQLite state tracking
