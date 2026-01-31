# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## ATP Backup

### 🟡 Medium Priority
- [ ] Cloud backup support via rclone Docker container

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

*No pending tasks - feature complete for current needs*

---

## Future Plugin Ideas

- [ ] ATP Docker Compose - manage multi-container stacks
- [ ] ATP UPS Monitor - advanced UPS management
- [ ] ATP Disk Health - SMART monitoring
- [ ] ATP Network Monitor - bandwidth tracking
