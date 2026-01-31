# ATP Shared Resources

Common CSS and JavaScript used by all ATP (A Tegenett Plugin) plugins.

## Structure

```
shared/
├── css/
│   └── atp-common.css    # Shared styles for all plugins
├── js/
│   └── atp-common.js     # Shared utilities (ATP.ajax, formatting, etc.)
└── README.md             # This file
```

## How It Works

The `build.py` script automatically injects shared resources into `.page` files:

1. CSS is injected after the opening `<style>` tag
2. JS is injected before the closing `</script>` tag
3. Plugin-specific prefixes get aliases (e.g., `--esc-*` maps to `--atp-*`)

## CSS Naming Convention

All shared CSS classes use the `atp-` prefix to avoid conflicts:

### Prefix System

| Prefix | Scope | Example |
|--------|-------|---------|
| `atp-` | Shared (all plugins) | `.atp-card`, `.atp-btn` |
| `tb-` | ATP Backup specific | `.tb-job-card` |
| `esc-` | ATP Emby specific | `.esc-cache-item` |

### CSS Variables

Theme colors defined in `:root`:

```css
/* Brand */
--atp-primary: #e67e22;      /* Orange - main brand color */
--atp-primary-dark: #d35400;
--atp-primary-light: #f39c12;

/* Status */
--atp-success: #27ae60;      /* Green */
--atp-danger: #c0392b;       /* Red */
--atp-warning: #f39c12;      /* Yellow */
--atp-info: #3498db;         /* Blue */

/* Theme-aware (from Unraid) */
--atp-bg: var(--body-background);
--atp-card-bg: var(--card-background);
--atp-text: var(--text-color);
--atp-text-muted: var(--text-muted);
--atp-border: var(--border-color);

/* Spacing */
--atp-spacing-xs: 5px;
--atp-spacing-sm: 10px;
--atp-spacing-md: 15px;
--atp-spacing-lg: 20px;
--atp-spacing-xl: 30px;

/* Border Radius */
--atp-radius-sm: 4px;
--atp-radius-md: 8px;
--atp-radius-lg: 12px;
```

### Component Classes

| Class | Purpose |
|-------|---------|
| `.atp-container` | Main container (max-width 1400px) |
| `.atp-header` | Page header with title/controls |
| `.atp-tabs` | Tab navigation |
| `.atp-tab` | Individual tab button |
| `.atp-panel` | Tab content panel |
| `.atp-card` | Content card with border |
| `.atp-section` | Alternative card style |
| `.atp-grid` | Auto-fit grid layout |
| `.atp-stat-card` | Dashboard statistic card |
| `.atp-btn` | Button base class |
| `.atp-btn-primary` | Orange button |
| `.atp-btn-success` | Green button |
| `.atp-btn-danger` | Red button |
| `.atp-table-wrapper` | Scrollable table container |
| `.atp-table` | Styled table |
| `.atp-form-group` | Form field wrapper |
| `.atp-log-viewer` | Terminal-style log display |
| `.atp-badge` | Inline status badge |
| `.atp-modal-overlay` | Modal backdrop |
| `.atp-modal` | Modal dialog |

### Modifier Classes

| Class | Effect |
|-------|--------|
| `.atp-btn-sm` | Small button |
| `.atp-btn-lg` | Large button |
| `.atp-status-badge.running` | Green status |
| `.atp-status-badge.stopped` | Red status |
| `.atp-hidden` | `display: none` |
| `.atp-text-center` | Center text |
| `.atp-spin` | Spinning animation |
| `.atp-pulse` | Pulsing animation |

### Utility Classes

| Class | Effect |
|-------|--------|
| `.atp-text-success` | Green text |
| `.atp-text-danger` | Red text |
| `.atp-text-warning` | Yellow text |
| `.atp-text-muted` | Gray text |
| `.atp-mt-lg` | Margin top 20px |
| `.atp-mb-lg` | Margin bottom 20px |

## JavaScript Utilities

The shared JS provides common functionality:

```javascript
// AJAX helper with CSRF
ATP.ajax(url, data, callback);

// Format file size
ATP.formatSize(bytes);  // "1.5 GB"

// Format duration
ATP.formatDuration(seconds);  // "2h 30m"

// Show toast notification
ATP.toast(message, type);  // type: 'success', 'error', 'warning', 'info'
```

## Adding New Shared Styles

1. Add styles to `shared/css/atp-common.css`
2. Use `atp-` prefix for all new classes
3. Add responsive rules in the media query sections
4. Document new classes in this README
5. Run `python build.py` to rebuild all plugins

## Plugin-Specific Styles

For styles only used in one plugin, add them directly to the `.page` file's `<style>` section using the plugin prefix (`tb-`, `esc-`, etc.).
