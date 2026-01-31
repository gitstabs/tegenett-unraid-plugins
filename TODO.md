# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## ATP Backup

### 🟠 High Priority
- [ ] Bandwidth scheduling (different limits at different times)

### 🟡 Medium Priority
- [ ] Snapshot/versioned backups (date-stamped folders)
- [ ] Export/import job configurations
- [ ] Weekly/monthly Discord summary reports
- [ ] Cloud backup support via rclone Docker container
- [ ] Telegram/Pushover/Slack notifications

### 🟢 Nice to Have
- [ ] Web-based file browser for source/destination selection
- [ ] Backup verification (checksum comparison)
- [ ] Compression option for backups

---

## ATP Emby Smart Cache

### 🟡 Medium Priority
- [x] ~~Improve logging and statistics~~ *(Already implemented - SQLite activity_log, /api/stats, Statistics tab)*
- [x] ~~Create proper documentation~~ *(Already complete in README.md)*

---

## Shared Components

### 🟡 Medium Priority
- [x] ~~Document CSS class naming convention~~ *(Added shared/README.md)*
- [ ] Fix plugin display names in Unraid Plugins list
- [ ] Create plugin template for new plugins
- [x] ~~Automated version bumping in build.py~~ *(Implemented --bump flag)*

---

## Infrastructure

### 🟡 Medium Priority
- [ ] Create development/testing guide
- [ ] Unit tests for Python daemon

---

## Branding & Design

### 🟢 Nice to Have
- [ ] Design uniform Tegenett logo for all plugins
- [ ] Design plugin-specific icons
- [ ] Color palette documentation

---

## Future Plugin Ideas

- [ ] ATP Docker Compose - manage multi-container stacks
- [ ] ATP UPS Monitor - advanced UPS management
- [ ] ATP Disk Health - SMART monitoring
- [ ] ATP Network Monitor - bandwidth tracking
