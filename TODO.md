# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## ATP Backup

### 🟠 High Priority
- [x] ~~Bandwidth scheduling (different limits at different times)~~ *(v2026.01.31 - Two profiles with start times)*

### 🟡 Medium Priority
- [ ] Snapshot/versioned backups (date-stamped folders)
- [x] ~~Export/import job configurations~~ *(v2026.01.31 - Export/Import jobs and settings as JSON)*
- [x] ~~Weekly/monthly Discord summary reports~~ *(v2026.01.31 - Configurable day/time for weekly and monthly)*
- [ ] Cloud backup support via rclone Docker container
- [ ] Telegram/Pushover/Slack notifications

### 🟢 Nice to Have
- [ ] Web-based file browser for source/destination selection
- [x] ~~Backup verification (checksum comparison)~~ *(v2026.01.31 - Per-job rsync --checksum option)*

### 🔮 Future Considerations
- [ ] Compression option for backups (tar.gz) - *Significant architecture change needed*

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
