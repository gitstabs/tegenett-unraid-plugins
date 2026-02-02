# Tegenett Unraid Plugins - TODO

## Priority Legend
- 🔴 Critical / Blocking
- 🟠 High priority
- 🟡 Medium priority
- 🟢 Low priority / Nice to have

---

## UI/Design Tasks

### ✅ Completed
- [x] Apply uniform tabs design to all ATP plugins (::after pattern)
- [x] Mobile responsive tabs fix for all plugins

---

## ATP Backup

### 🟡 Medium Priority
- [ ] Cloud backup support via rclone Docker container

### 🔮 Future Considerations
- [ ] Compression option for backups (tar.gz)
- [ ] Snapshot/versioned backups (date-stamped folders)

---

## ATP Emby Smart Cache

*No pending tasks - feature complete for current needs*

---

## ATP LSI Monitor

*No pending tasks - feature complete for current needs*

---

## Future Plugin Ideas

### 🟠 High Interest

#### ATP Power Monitor ⚡
Supplement to NUT/PeaNUT - focuses on what they don't do well:
- Power consumption tracking over time (kWh)
- Estimated electricity cost per month (configurable rate)
- "What does my server cost me?" dashboard
- Historical graphs and trends
- Cost comparison (this month vs last month)
- Budget alerts ("You've exceeded 50 kWh this month")
- **UPS Quirks Database**: Translate confusing status codes to human-readable text
  - "OL DISCHRG" → "Normal (AVR active)" when battery > 95%
  - Known firmware bugs (battery.mfr.date: 1980/01/01)
  - Model-specific status interpretations
- **Status Anomaly Detection**: Alert when status seems wrong
  - "Discharging" but battery at 100%? Probably firmware quirk
  - Conflicting flags explained in plain language
- **Modern UI**: Better than NUT's default interface
  - Real-time status with clear icons
  - Battery health visualization
  - Power flow diagram (Mains → UPS → Server)

### 🟡 Medium Interest

#### ATP Self-Healer 🔧
Auto-restart Docker containers and VMs that crash:
- Health monitoring beyond Docker's built-in
- Discord/webhook notifications when something is auto-fixed
- Crash history and auto-fix logs
- Configurable restart policies per container

#### ATP Service Status 📊
Dashboard for all self-hosted services:
- HTTP health checks for any URL
- Response time tracking
- "Plex is down!" push notifications
- Uptime percentage display
- Simple status page generation

#### ATP Speed Test 🚀
Automated internet speed tests with history:
- Speedtest.net CLI integration
- Graphs over time
- "Your ISP is only delivering 80% of what you pay for"
- Scheduled tests (daily/weekly)

#### ATP Certificate Manager 🔐
SSL certificate overview and alerts:
- Monitor all HTTPS domains you own
- "Certificate expires in 14 days!" notifications
- Let's Encrypt renewal tracking
- Dashboard with all cert statuses

### 🟢 Low Priority / Future

#### ATP Network Scanner 🌐
Overview of all devices on your network:
- New device = alert
- IP/MAC/hostname tracking
- "Who's stealing bandwidth?" overview

#### ATP Disk Predictor 💾
SMART analysis with predictive failure warnings:
- Trend analysis over time
- "This disk should be replaced within 3 months"
- Compare with database of known disk failure rates

#### ATP Docker Compose 🐳
Manage multi-container stacks:
- Import docker-compose.yml
- One-click deploy/update
- Stack-based view

#### ATP Wake Scheduler ⏰
Advanced WOL + shutdown scheduling:
- "Start server at 06:00, shutdown at 02:00"
- Calendar integration
- Smart wake based on Plex/Emby activity

#### ATP Backup Integrity ✅
Verify that backups are actually readable:
- Periodic restore tests (to temp location)
- Hash verification
- "Your backup from 3 days ago is corrupt!" alerts
