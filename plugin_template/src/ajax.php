<?php
/**
 * ATP Template - AJAX Handler
 * v2026.01.31
 *
 * Proxies requests to Python daemon API.
 * Replace 'atp_template' with your plugin name throughout.
 *
 * SECURITY: CSRF validation for Unraid 7.x
 */

// ============================================
// CONFIGURATION
// ============================================

$PLUGIN_NAME = 'atp_template';
$CONFIG_FILE = "/boot/config/plugins/{$PLUGIN_NAME}/settings.json";
$API_PORT = 39999; // Default port - change this!
$API_HOST = "127.0.0.1";

// Read port from settings if available
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
    'create_item', 'update_item', 'delete_item',
    'save_settings', 'service'
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

// ============================================
// API HELPER
// ============================================

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
        return ['success' => false, 'error' => 'Invalid API response'];
    }

    return $decoded;
}

// ============================================
// POST DATA HELPER
// ============================================

function getPostData() {
    $contentType = $_SERVER['CONTENT_TYPE'] ?? '';

    if (strpos($contentType, 'application/json') !== false) {
        return json_decode(file_get_contents('php://input'), true) ?: [];
    }

    // Form-urlencoded data
    $data = $_POST;

    // Remove csrf_token from data sent to API
    unset($data['csrf_token']);
    unset($data['action']);

    // Convert string booleans
    foreach ($data as $key => $value) {
        if ($value === 'true') $data[$key] = true;
        if ($value === 'false') $data[$key] = false;
    }

    return $data;
}

// ============================================
// REQUEST ROUTING
// ============================================

header('Content-Type: application/json');

switch ($action) {

    // Status
    case 'status':
        echo json_encode(apiCall('/api/status'));
        break;

    // Items
    case 'get_items':
        echo json_encode(apiCall('/api/items'));
        break;

    case 'get_item':
        $id = intval($_REQUEST['id'] ?? 0);
        echo json_encode(apiCall("/api/items/{$id}"));
        break;

    case 'create_item':
        $data = getPostData();
        echo json_encode(apiCall('/api/items', 'POST', $data));
        break;

    case 'update_item':
        $id = intval($_REQUEST['id'] ?? 0);
        $data = getPostData();
        unset($data['id']);
        echo json_encode(apiCall("/api/items/{$id}", 'PUT', $data));
        break;

    case 'delete_item':
        $id = intval($_REQUEST['id'] ?? 0);
        echo json_encode(apiCall("/api/items/{$id}", 'DELETE'));
        break;

    // Settings
    case 'get_settings':
        echo json_encode(apiCall('/api/settings'));
        break;

    case 'save_settings':
        $data = getPostData();
        echo json_encode(apiCall('/api/settings', 'POST', $data));
        break;

    // Logs
    case 'get_logs':
        $lines = intval($_REQUEST['lines'] ?? 200);
        global $PLUGIN_NAME;
        $result = apiCall("/api/logs?lines={$lines}");

        // Fallback: read log file directly if API fails
        if (!$result['success']) {
            $logFile = "/mnt/user/appdata/{$PLUGIN_NAME}/logs/{$PLUGIN_NAME}.log";
            if (file_exists($logFile)) {
                $logLines = file($logFile);
                $logLines = array_slice($logLines, -$lines);
                $result = ['success' => true, 'logs' => implode("", $logLines)];
            }
        }
        echo json_encode($result);
        break;

    // Service control
    case 'service':
        $cmd = $_REQUEST['cmd'] ?? '';
        $validCmds = ['start', 'stop', 'restart', 'status'];

        if (!in_array($cmd, $validCmds)) {
            echo json_encode(['success' => false, 'error' => 'Invalid command']);
            break;
        }

        global $PLUGIN_NAME;
        $script = "/usr/local/emhttp/plugins/{$PLUGIN_NAME}/rc.{$PLUGIN_NAME}";
        exec("{$script} {$cmd} 2>&1", $output, $returnCode);

        echo json_encode([
            'success' => $returnCode === 0,
            'output' => implode("\n", $output),
            'code' => $returnCode
        ]);
        break;

    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
        break;
}
