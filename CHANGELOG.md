# Changelog

All notable changes to Tegenett Unraid Plugins.

---

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
