# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## ATP Backup

### 🟠 High Priority
- [x] ~~Bandwidth scheduling (different limits at different times)~~ *(v2026.01.31a - Two profiles with start times)*

### 🟡 Medium Priority
- [x] ~~Export/import job configurations~~ *(v2026.01.31a - Export/Import jobs and settings as JSON)*
- [x] ~~Weekly/monthly Discord summary reports~~ *(v2026.01.31a - Configurable day/time for weekly and monthly)*
- [ ] Cloud backup support via rclone Docker container

### 🟢 Nice to Have
- [x] ~~Backup verification (checksum comparison)~~ *(v2026.01.31a - Per-job rsync --checksum option)*

### 🔮 Future Considerations
- [ ] Compression option for backups (tar.gz) - *Significant architecture change needed*
- [ ] Snapshot/versioned backups (date-stamped folders) - *Useful for rollback, needs storage planning*
- [ ] Alternative notification channels:

| Service | Privacy | Self-Hosted | Notes |
|---------|---------|-------------|-------|
| Discord | Medium | No | Current implementation, requires Discord account |
| Telegram | Low | No | Phone number required, linked to identity |
| Pushover | High | No | Paid ($5 one-time), no personal data required |
| Slack | Medium | No | Requires workspace, good for teams |
| Gotify | High | Yes | Self-hosted, fully private, recommended |
| ntfy | High | Yes/No | Can self-host or use public server |

---

## ATP Emby Smart Cache

### 🟡 Medium Priority
- [x] ~~Improve logging and statistics~~ *(Already implemented - SQLite activity_log, /api/stats, Statistics tab)*
- [x] ~~Create proper documentation~~ *(Already complete in README.md)*

---

## Shared Components

### 🟡 Medium Priority
- [x] ~~Document CSS class naming convention~~ *(Added shared/README.md)*
- [x] ~~Fix plugin display names in Unraid Plugins list~~ *(v2026.01.31d - README.md included in PLG)*
- [x] ~~Create plugin template for new plugins~~ *(v2026.01.31 - Full template in plugin_template/)*
- [x] ~~Automated version bumping in build.py~~ *(Implemented --bump flag)*

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
