<?php
/**
 * ATP Emby Smart Cache - AJAX Handler v2026.01.29
 * Standalone AJAX handler - bypasses Unraid's page template system
 */
error_reporting(0);
ini_set('display_errors', 0);
header('Content-Type: application/json');

$plugin = "atp_emby_smart_cache";
$configFile = "/boot/config/plugins/{$plugin}/settings.json";

// Auto-detect server IP from HTTP_HOST (strips port if present)
$serverIp = isset($_SERVER['HTTP_HOST']) ? preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST']) : '127.0.0.1';

$defaults = [
    "ENABLED" => false,
    "EMBY_HOST" => "",
    "EMBY_API_KEY" => "",
    "DISCORD_WEBHOOK_URL" => "",
    "SERVER_PORT" => 9999,
    "UNRAID_USER_PATH" => "/mnt/user",
    "CACHE_PATH" => "/mnt/cache",
    "ARRAY_ONLY_PATH" => "/mnt/user0",
    "LOG_FILE_PATH" => "/mnt/user/appdata/atp_emby_smart_cache/logs/atp_emby_smart_cache.log",
    "RSYNC_BWLIMIT" => "0",
    "MIN_FREE_SPACE_GB" => 100,
    "MAX_FILE_SIZE_GB" => 0,
    "SKIP_HARDLINKS" => true,
    "DELETE_ON_STOP" => true,
    "CLEANUP_DELAY_HOURS" => 24,
    "MOVER_IGNORE_FILE" => "",
    "ALLOWED_EXTS" => ".mkv,.mp4,.m4v,.avi,.mov,.ts",
    "EXCLUDE_PATHS" => "",
    "DOCKER_PATH_MAP" => "",
    "COOLDOWN_MOVIE_SEC" => 60,
    "COOLDOWN_EPISODE_SEC" => 30,
    "PRECACHE_EPISODES" => 1,
    "RSYNC_RETRIES" => 3,
    "LOG_RETENTION" => 5,
    "LOG_LEVEL" => "INFO"
];

$settings = $defaults;
if (file_exists($configFile)) {
    $loaded = json_decode(file_get_contents($configFile), true);
    if ($loaded) $settings = array_merge($defaults, $loaded);
}

function apiCall($endpoint, $method = 'GET', $data = null, $timeout = 5) {
    global $settings, $serverIp;
    $port = isset($settings['SERVER_PORT']) ? intval($settings['SERVER_PORT']) : 9999;
    // Use detected server IP instead of 127.0.0.1 (PHP in Unraid can't reach localhost)
    $url = "http://{$serverIp}:{$port}{$endpoint}";

    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 3);
        if ($method === 'POST' && $data !== null) {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        }
        $resp = curl_exec($ch);
        $err = curl_error($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if (!$err && $resp !== false) {
            $decoded = json_decode($resp, true);
            if ($decoded !== null) return $decoded;
        }
        return ['success' => false, 'error' => $err ?: "HTTP {$code}"];
    }

    // Fallback to file_get_contents
    $ctx = stream_context_create(['http' => ['timeout' => $timeout]]);
    $resp = @file_get_contents($url, false, $ctx);
    if ($resp !== false) {
        $decoded = json_decode($resp, true);
        if ($decoded !== null) return $decoded;
    }
    return ['success' => false, 'error' => 'Connection failed'];
}

$action = isset($_POST['ajax']) ? $_POST['ajax'] : (isset($_GET['ajax']) ? $_GET['ajax'] : '');

if (empty($action)) {
    echo json_encode(['success' => false, 'error' => 'No action specified']);
    exit;
}

switch ($action) {
    case 'get_status':
        echo json_encode(apiCall('/api/status'));
        break;

    case 'get_managed':
        echo json_encode(apiCall('/api/managed'));
        break;

    case 'get_queue':
        echo json_encode(apiCall('/api/queue'));
        break;

    case 'get_logs':
        $lines = isset($_POST['lines']) ? intval($_POST['lines']) : 100;
        $result = apiCall("/api/logs?lines={$lines}");
        if (!$result['success']) {
            // Fallback: read log file directly
            $logPath = $settings['LOG_FILE_PATH'];
            if (file_exists($logPath)) {
                $logLines = file($logPath, FILE_IGNORE_NEW_LINES);
                $logLines = array_slice($logLines, -$lines);
                $result = ['success' => true, 'logs' => implode("\n", $logLines)];
            }
        }
        echo json_encode($result);
        break;

    case 'get_mover':
        $result = apiCall('/api/mover_ignore');
        if (!$result['success']) {
            $moverFile = $settings['MOVER_IGNORE_FILE'];
            if (!empty($moverFile) && file_exists($moverFile)) {
                $result = ['success' => true, 'content' => file_get_contents($moverFile)];
            } else {
                $result = ['success' => true, 'content' => '(not configured)'];
            }
        }
        echo json_encode($result);
        break;

    case 'get_history':
        echo json_encode(apiCall('/api/history'));
        break;

    case 'get_health':
        echo json_encode(apiCall('/api/health'));
        break;

    case 'get_stats':
        echo json_encode(apiCall('/api/stats'));
        break;

    case 'force_cleanup':
        $path = isset($_POST['path']) ? $_POST['path'] : '';
        // Use 120 second timeout for large file operations
        echo json_encode(apiCall('/api/cleanup', 'POST', ['path' => $path], 120));
        break;

    case 'rebuild_state':
        // Use 60 second timeout for state rebuild
        echo json_encode(apiCall('/api/rebuild', 'POST', [], 60));
        break;

    case 'reset_stats':
        // Reset statistics
        echo json_encode(apiCall('/api/reset_stats', 'POST', [], 30));
        break;

    case 'clear_log':
        $logPath = $settings['LOG_FILE_PATH'];
        if (file_exists($logPath)) {
            file_put_contents($logPath, "");
            echo json_encode(['success' => true, 'message' => 'Log cleared']);
        } else {
            echo json_encode(['success' => false, 'error' => 'Log file not found']);
        }
        break;

    case 'save_settings':
        $new = $defaults;
        foreach ($defaults as $k => $v) {
            if (isset($_POST[$k])) {
                if (is_bool($v) || in_array($k, ['ENABLED','SKIP_HARDLINKS','DELETE_ON_STOP'])) {
                    $new[$k] = ($_POST[$k] === 'true' || $_POST[$k] === '1');
                } else {
                    $new[$k] = trim($_POST[$k]);
                }
            }
        }
        $saved = file_put_contents($configFile, json_encode($new, JSON_PRETTY_PRINT));
        exec("/usr/local/emhttp/plugins/{$plugin}/rc.atp_emby_smart_cache restart 2>&1", $out);
        echo json_encode(['success' => $saved !== false, 'message' => 'Settings saved, service restarted']);
        break;

    case 'debug':
        $port = $settings['SERVER_PORT'];
        $apiUrl = "http://{$serverIp}:{$port}/api/status";
        $debug = [
            'php_version' => PHP_VERSION,
            'curl_available' => function_exists('curl_init'),
            'server_ip' => $serverIp,
            'port' => $port,
            'api_url' => $apiUrl,
            'config_exists' => file_exists($configFile)
        ];

        // Test curl with server IP
        if (function_exists('curl_init')) {
            $ch = curl_init($apiUrl);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 3);
            $resp = curl_exec($ch);
            $debug['curl_response'] = substr($resp ?: '', 0, 200);
            $debug['curl_error'] = curl_error($ch);
            $debug['curl_http_code'] = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
        }

        echo json_encode(['success' => true, 'debug' => $debug]);
        break;

    case 'service_start':
        exec("/usr/local/emhttp/plugins/{$plugin}/rc.atp_emby_smart_cache start 2>&1", $out, $ret);
        sleep(1); // Wait for service to start
        $pidFile = "/var/run/{$plugin}.pid";
        $pid = file_exists($pidFile) ? trim(file_get_contents($pidFile)) : null;
        echo json_encode(['success' => $ret === 0, 'message' => implode("\n", $out), 'pid' => $pid]);
        break;

    case 'service_stop':
        exec("/usr/local/emhttp/plugins/{$plugin}/rc.atp_emby_smart_cache stop 2>&1", $out, $ret);
        echo json_encode(['success' => $ret === 0, 'message' => implode("\n", $out)]);
        break;

    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action: ' . $action]);
}
