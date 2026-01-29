<?php
/**
 * ATP Backup - AJAX Handler v2026.01.30
 * Proxies requests to Python daemon API
 *
 * SECURITY: CSRF validation for Unraid 7.x
 */

// Read port from settings
$CONFIG_FILE = "/boot/config/plugins/atp_backup/settings.json";
$API_PORT = 39982; // Default port
$API_HOST = "127.0.0.1";

if (file_exists($CONFIG_FILE)) {
    $config = json_decode(file_get_contents($CONFIG_FILE), true);
    if (isset($config['SERVER_PORT'])) {
        $API_PORT = intval($config['SERVER_PORT']);
    }
}

// ============================================
// CSRF VALIDATION (Unraid 7.x Security)
// ============================================
// Actions that modify state require CSRF validation
$modifying_actions = [
    'create_job', 'update_job', 'toggle_job', 'delete_job', 'run_job',
    'save_settings', 'service', 'abort',
    'clear_history', 'reset_statistics', 'reset_database'
];

$action = $_REQUEST['action'] ?? '';

// Validate CSRF token for modifying operations
if (in_array($action, $modifying_actions)) {
    $csrf_token = $_POST['csrf_token'] ?? $_GET['csrf_token'] ?? $_REQUEST['csrf_token'] ?? '';
    $valid_csrf = false;

    // Read Unraid's CSRF token from var.ini
    $var_file = '/var/local/emhttp/var.ini';
    if (file_exists($var_file)) {
        $var = @parse_ini_file($var_file);
        if ($var && isset($var['csrf_token'])) {
            $valid_csrf = hash_equals($var['csrf_token'], $csrf_token);
        }
    }

    if (!$valid_csrf) {
        header('Content-Type: application/json');
        echo json_encode(['success' => false, 'error' => 'Invalid or missing CSRF token']);
        exit;
    }
}

// Helper function to make API requests
function apiCall($endpoint, $method = 'GET', $data = null) {
    global $API_PORT, $API_HOST;

    $url = "http://{$API_HOST}:{$API_PORT}{$endpoint}";

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);

    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        if ($data) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        }
    } elseif ($method === 'PUT') {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
        if ($data) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        }
    } elseif ($method === 'DELETE') {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'DELETE');
    }

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $curlError = curl_error($ch);
    curl_close($ch);

    if ($curlError) {
        return ['success' => false, 'error' => "API unavailable: {$curlError}"];
    }

    if (empty($response)) {
        return ['success' => false, 'error' => 'Empty response from API'];
    }

    $decoded = json_decode($response, true);
    if ($decoded === null) {
        return ['success' => false, 'error' => 'Invalid API response: ' . substr($response, 0, 100)];
    }

    return $decoded;
}

// Get POST data - handles both JSON and form-urlencoded
function getPostData() {
    $contentType = $_SERVER['CONTENT_TYPE'] ?? '';

    if (strpos($contentType, 'application/json') !== false) {
        return json_decode(file_get_contents('php://input'), true) ?: [];
    }

    // Form-urlencoded data (from URLSearchParams)
    $data = $_POST;

    // Remove csrf_token from data sent to API
    unset($data['csrf_token']);

    // Convert string booleans
    foreach ($data as $key => $value) {
        if ($value === 'true') $data[$key] = true;
        if ($value === 'false') $data[$key] = false;
    }

    return $data;
}

header('Content-Type: application/json');

switch ($action) {

    case 'status':
        echo json_encode(apiCall('/api/status'));
        break;
    
    case 'get_jobs':
        echo json_encode(apiCall('/api/jobs'));
        break;
    
    case 'get_job':
        $id = intval($_REQUEST['id'] ?? 0);
        echo json_encode(apiCall("/api/jobs/{$id}"));
        break;
    
    case 'create_job':
        $data = getPostData();
        echo json_encode(apiCall('/api/jobs', 'POST', $data));
        break;
    
    case 'update_job':
        $id = intval($_REQUEST['id'] ?? 0);
        $data = getPostData();
        unset($data['id']); // Remove id from data, it's in URL
        echo json_encode(apiCall("/api/jobs/{$id}", 'PUT', $data));
        break;
    
    case 'toggle_job':
        $id = intval($_REQUEST['id'] ?? 0);
        $enabled = intval($_REQUEST['enabled'] ?? 0);
        echo json_encode(apiCall("/api/jobs/{$id}/toggle", 'POST', ['enabled' => $enabled]));
        break;
    
    case 'delete_job':
        $id = intval($_REQUEST['id'] ?? 0);
        echo json_encode(apiCall("/api/jobs/{$id}", 'DELETE'));
        break;
    
    case 'run_job':
        $id = intval($_REQUEST['id'] ?? 0);
        $dryRun = ($_REQUEST['dry_run'] ?? 'false') === 'true';
        echo json_encode(apiCall("/api/jobs/{$id}/run", 'POST', ['dry_run' => $dryRun]));
        break;
    
    case 'get_history':
        $limit = intval($_REQUEST['limit'] ?? 100);
        $jobId = $_REQUEST['job_id'] ?? '';
        $query = "?limit={$limit}";
        if ($jobId) $query .= "&job_id={$jobId}";
        echo json_encode(apiCall("/api/history{$query}"));
        break;
    
    case 'get_stats':
        $days = intval($_REQUEST['days'] ?? 30);
        echo json_encode(apiCall("/api/stats?days={$days}"));
        break;
    
    case 'get_logs':
        $lines = intval($_REQUEST['lines'] ?? 200);
        $result = apiCall("/api/logs?lines={$lines}");
        
        // Fallback: read log file directly if API fails
        if (!$result['success']) {
            $logFile = '/mnt/user/appdata/atp_backup/logs/atp_backup.log';
            if (file_exists($logFile)) {
                $logLines = file($logFile);
                $logLines = array_slice($logLines, -$lines);
                $result = ['success' => true, 'logs' => implode("", $logLines)];
            }
        }
        echo json_encode($result);
        break;
    
    case 'get_settings':
        echo json_encode(apiCall('/api/settings'));
        break;
    
    case 'save_settings':
        $data = getPostData();
        echo json_encode(apiCall('/api/settings', 'POST', $data));
        break;
    
    case 'test_wol':
        $mac = $_REQUEST['mac_address'] ?? '';
        echo json_encode(apiCall('/api/test/wol', 'POST', ['mac_address' => $mac]));
        break;
    
    case 'test_ping':
        $host = $_REQUEST['host'] ?? '';
        echo json_encode(apiCall('/api/test/ping', 'POST', ['host' => $host]));
        break;
    
    case 'test_discord':
        echo json_encode(apiCall('/api/test/discord', 'POST'));
        break;
    
    case 'test_mount':
        $share = $_REQUEST['share'] ?? '';
        echo json_encode(apiCall('/api/test/mount', 'POST', ['share' => $share]));
        break;
    
    case 'service':
        $cmd = $_REQUEST['cmd'] ?? '';
        $validCmds = ['start', 'stop', 'restart', 'status'];
        
        if (!in_array($cmd, $validCmds)) {
            echo json_encode(['success' => false, 'error' => 'Invalid command']);
            break;
        }
        
        $script = '/usr/local/emhttp/plugins/atp_backup/rc.atp_backup';
        exec("{$script} {$cmd} 2>&1", $output, $returnCode);
        
        echo json_encode([
            'success' => $returnCode === 0,
            'output' => implode("\n", $output),
            'code' => $returnCode
        ]);
        break;
    
    case 'abort':
        echo json_encode(apiCall('/api/abort', 'POST'));
        break;
    
    case 'clear_history':
        echo json_encode(apiCall('/api/database/clear_history', 'POST'));
        break;
    
    case 'reset_statistics':
        echo json_encode(apiCall('/api/database/reset_statistics', 'POST'));
        break;
    
    case 'reset_database':
        echo json_encode(apiCall('/api/database/reset', 'POST'));
        break;
    
    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
        break;
}
