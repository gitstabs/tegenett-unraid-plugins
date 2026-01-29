/**
 * ATP COMMON JS - v2026.01.30
 * Shared JavaScript utilities for all ATP plugins
 * Injected automatically by build.py
 */

var ATP = ATP || {};

/**
 * Initialize ATP utilities
 * @param {Object} options - Configuration options
 * @param {string} options.prefix - Plugin prefix (e.g., 'tb', 'esc')
 * @param {string} options.ajaxUrl - AJAX endpoint URL
 * @param {string} options.csrfToken - CSRF token for security
 */
ATP.init = function(options) {
    this.prefix = options.prefix || 'atp';
    this.ajaxUrl = options.ajaxUrl || '';
    this.csrfToken = options.csrfToken || '';
    this.refreshInterval = options.refreshInterval || 3000;
    this.refreshTimer = null;
    this.countdown = this.refreshInterval / 1000;
    this.currentTab = 'dashboard';

    console.log('[ATP] Initialized with prefix:', this.prefix);
};

/**
 * Get CSRF token from page or stored value
 * @returns {string} CSRF token
 */
ATP.getCsrfToken = function() {
    if (this.csrfToken) return this.csrfToken;

    // Try to get from hidden input
    var input = document.querySelector('input[name="csrf_token"]');
    if (input) return input.value;

    // Try to get from meta tag
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');

    return '';
};

/**
 * Make AJAX request with CSRF token
 * @param {string} action - AJAX action name
 * @param {Object} data - Additional data to send
 * @param {Function} callback - Success callback
 * @param {Function} errorCallback - Error callback
 */
ATP.ajax = function(action, data, callback, errorCallback) {
    var self = this;
    data = data || {};
    data.ajax = action;
    data.csrf_token = this.getCsrfToken();

    $.ajax({
        url: this.ajaxUrl,
        method: 'POST',
        data: data,
        dataType: 'json',
        timeout: 30000
    }).done(function(response) {
        if (callback) callback(response);
    }).fail(function(xhr, status, error) {
        console.error('[ATP] AJAX error:', action, status, error);
        if (errorCallback) {
            errorCallback(error, xhr);
        }
    });
};

/**
 * Make AJAX request with extended timeout (for long operations)
 * @param {string} action - AJAX action name
 * @param {Object} data - Additional data to send
 * @param {number} timeout - Timeout in milliseconds
 * @param {Function} callback - Success callback
 * @param {Function} errorCallback - Error callback
 */
ATP.ajaxLong = function(action, data, timeout, callback, errorCallback) {
    var self = this;
    data = data || {};
    data.ajax = action;
    data.csrf_token = this.getCsrfToken();

    $.ajax({
        url: this.ajaxUrl,
        method: 'POST',
        data: data,
        dataType: 'json',
        timeout: timeout || 120000
    }).done(function(response) {
        if (callback) callback(response);
    }).fail(function(xhr, status, error) {
        console.error('[ATP] AJAX long error:', action, status, error);
        if (errorCallback) {
            errorCallback(error, xhr);
        }
    });
};

/* ============================================
   FORMATTING UTILITIES
   ============================================ */

/**
 * Format bytes to human readable string
 * @param {number} bytes - Number of bytes
 * @param {number} decimals - Decimal places (default: 2)
 * @returns {string} Formatted string (e.g., "1.5 GB")
 */
ATP.formatBytes = function(bytes, decimals) {
    if (bytes === 0 || bytes === null || bytes === undefined) return '0 B';
    decimals = decimals !== undefined ? decimals : 2;

    var k = 1024;
    var sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
    var i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
};

/**
 * Format seconds to human readable duration
 * @param {number} seconds - Number of seconds
 * @returns {string} Formatted duration (e.g., "2h 30m")
 */
ATP.formatDuration = function(seconds) {
    if (!seconds || isNaN(seconds) || seconds <= 0) return '-';

    seconds = Math.floor(seconds);

    if (seconds < 60) {
        return seconds + 's';
    }
    if (seconds < 3600) {
        var m = Math.floor(seconds / 60);
        var s = seconds % 60;
        return m + 'm ' + s + 's';
    }
    if (seconds < 86400) {
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        return h + 'h ' + m + 'm';
    }

    var d = Math.floor(seconds / 86400);
    var h = Math.floor((seconds % 86400) / 3600);
    return d + 'd ' + h + 'h';
};

/**
 * Format countdown timer
 * @param {number} seconds - Seconds remaining
 * @returns {string} Formatted countdown (e.g., "5m 30s")
 */
ATP.formatCountdown = function(seconds) {
    if (seconds <= 0) return 'Now';
    return this.formatDuration(seconds);
};

/**
 * Format timestamp to locale string
 * @param {number|string} timestamp - Unix timestamp or ISO string
 * @returns {string} Formatted date/time
 */
ATP.formatTimestamp = function(timestamp) {
    if (!timestamp) return '-';

    var date;
    if (typeof timestamp === 'number') {
        date = new Date(timestamp * 1000);
    } else {
        date = new Date(timestamp);
    }

    if (isNaN(date.getTime())) return '-';

    return date.toLocaleString();
};

/**
 * Format relative time (e.g., "5 minutes ago")
 * @param {number|string} timestamp - Unix timestamp or ISO string
 * @returns {string} Relative time string
 */
ATP.formatRelativeTime = function(timestamp) {
    if (!timestamp) return '-';

    var date;
    if (typeof timestamp === 'number') {
        date = new Date(timestamp * 1000);
    } else {
        date = new Date(timestamp);
    }

    if (isNaN(date.getTime())) return '-';

    var seconds = Math.floor((Date.now() - date.getTime()) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' min ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
    if (seconds < 604800) return Math.floor(seconds / 86400) + ' days ago';

    return date.toLocaleDateString();
};

/* ============================================
   STRING UTILITIES
   ============================================ */

/**
 * Escape HTML entities to prevent XSS
 * @param {string} str - String to escape
 * @returns {string} Escaped string
 */
ATP.escapeHtml = function(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
};

/**
 * Truncate string with ellipsis
 * @param {string} str - String to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated string
 */
ATP.truncate = function(str, maxLength) {
    if (!str) return '';
    maxLength = maxLength || 50;
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength - 3) + '...';
};

/**
 * Get filename from path
 * @param {string} path - Full file path
 * @returns {string} Filename only
 */
ATP.getFilename = function(path) {
    if (!path) return '';
    return path.split('/').pop().split('\\').pop();
};

/* ============================================
   TAB MANAGEMENT
   ============================================ */

/**
 * Initialize tab switching
 * @param {string} tabSelector - Selector for tab elements
 * @param {string} panelPrefix - Prefix for panel IDs
 * @param {Function} onTabChange - Callback when tab changes
 */
ATP.initTabs = function(tabSelector, panelPrefix, onTabChange) {
    var self = this;
    tabSelector = tabSelector || '.atp-tab';
    panelPrefix = panelPrefix || '#panel-';

    $(tabSelector).click(function() {
        var tab = $(this).data('tab');

        // Update tab active state
        $(tabSelector).removeClass('active');
        $(this).addClass('active');

        // Update panel visibility
        $('.atp-panel').removeClass('active');
        $(panelPrefix + tab).addClass('active');

        self.currentTab = tab;

        if (onTabChange) {
            onTabChange(tab);
        }
    });
};

/* ============================================
   AUTO-REFRESH
   ============================================ */

/**
 * Start auto-refresh timer
 * @param {Function} refreshFunction - Function to call on refresh
 * @param {string} countdownSelector - Selector for countdown display
 */
ATP.startRefresh = function(refreshFunction, countdownSelector) {
    var self = this;
    countdownSelector = countdownSelector || '#refresh-countdown';

    this.stopRefresh();

    // Initial refresh
    if (refreshFunction) refreshFunction();

    this.countdown = this.refreshInterval / 1000;
    $(countdownSelector).text(this.countdown);

    this.refreshTimer = setInterval(function() {
        self.countdown--;
        $(countdownSelector).text(self.countdown);

        if (self.countdown <= 0) {
            self.countdown = self.refreshInterval / 1000;
            if (refreshFunction) refreshFunction();
        }
    }, 1000);
};

/**
 * Stop auto-refresh timer
 */
ATP.stopRefresh = function() {
    if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
        this.refreshTimer = null;
    }
};

/* ============================================
   DIALOG HELPERS
   ============================================ */

/**
 * Show confirmation dialog using SweetAlert or fallback
 * @param {Object} options - Dialog options
 * @param {string} options.title - Dialog title
 * @param {string} options.text - Dialog message
 * @param {string} options.type - Dialog type (warning, info, success, error)
 * @param {Function} callback - Called with true/false
 */
ATP.confirm = function(options, callback) {
    if (typeof swal !== 'undefined') {
        swal({
            title: options.title || 'Confirm',
            text: options.text || 'Are you sure?',
            type: options.type || 'warning',
            showCancelButton: true,
            confirmButtonColor: options.type === 'warning' ? '#f44336' : '#e67e22'
        }, function(confirmed) {
            if (callback) callback(confirmed);
        });
    } else {
        var result = confirm(options.text || 'Are you sure?');
        if (callback) callback(result);
    }
};

/**
 * Show alert dialog using SweetAlert or fallback
 * @param {Object} options - Dialog options
 * @param {string} options.title - Dialog title
 * @param {string} options.text - Dialog message
 * @param {string} options.type - Dialog type (success, error, info, warning)
 */
ATP.alert = function(options) {
    if (typeof swal !== 'undefined') {
        swal({
            title: options.title || 'Alert',
            text: options.text || '',
            type: options.type || 'info'
        });
    } else {
        alert((options.title ? options.title + '\n\n' : '') + (options.text || ''));
    }
};

/**
 * Show loading dialog
 * @param {string} title - Loading title
 * @param {string} text - Loading message
 */
ATP.showLoading = function(title, text) {
    if (typeof swal !== 'undefined') {
        swal({
            title: title || 'Processing...',
            text: text || 'Please wait...',
            type: 'info',
            showConfirmButton: false
        });
    }
};

/**
 * Close any open dialog
 */
ATP.closeDialog = function() {
    if (typeof swal !== 'undefined') {
        swal.close();
    }
};

/* ============================================
   BUTTON STATE HELPERS
   ============================================ */

/**
 * Set button to loading state
 * @param {jQuery|string} button - Button element or selector
 * @param {string} loadingText - Text to show while loading
 */
ATP.setButtonLoading = function(button, loadingText) {
    var $btn = $(button);
    var $icon = $btn.find('i').first();
    var $text = $btn.find('span').first();

    $btn.prop('disabled', true);
    $btn.data('original-icon', $icon.attr('class'));
    $btn.data('original-text', $text.text());

    $icon.attr('class', 'fa fa-spinner fa-spin');
    if (loadingText) $text.text(loadingText);
};

/**
 * Reset button from loading state
 * @param {jQuery|string} button - Button element or selector
 * @param {boolean} success - Whether operation was successful
 * @param {string} resultText - Optional text to show briefly
 */
ATP.resetButton = function(button, success, resultText) {
    var $btn = $(button);
    var $icon = $btn.find('i').first();
    var $text = $btn.find('span').first();

    var originalIcon = $btn.data('original-icon');
    var originalText = $btn.data('original-text');

    // Show result briefly
    $icon.attr('class', success ? 'fa fa-check' : 'fa fa-times');
    if (resultText) $text.text(resultText);

    setTimeout(function() {
        $btn.prop('disabled', false);
        $icon.attr('class', originalIcon || 'fa fa-save');
        $text.text(originalText || 'Save');
    }, 1500);
};

/* ============================================
   EXPORT FOR CommonJS/AMD
   ============================================ */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ATP;
} else if (typeof define === 'function' && define.amd) {
    define(function() { return ATP; });
}
