<?php
declare(strict_types=1);
require __DIR__ . '/../config.php';
startSecureSession();
header('Cache-Control: no-store');
if (empty($_SESSION[SESSION_KEY])) { http_response_code(403); exit('Login required'); }
$hash = getenv('VENTURE_OWNER_PASS_HASH') ?: '';
$endpoint = getenv('VENTURE_OWNER_API_URL') ?: '';
$token = getenv('VENTURE_OWNER_API_TOKEN') ?: '';
$cert = getenv('VENTURE_OWNER_CLIENT_CERT') ?: '';
$key = getenv('VENTURE_OWNER_CLIENT_KEY') ?: '';
$ca = getenv('VENTURE_OWNER_CA') ?: '';
$ready = $hash !== '' && str_starts_with($endpoint, 'https://') && strlen($token) >= 32
    && is_readable($cert) && is_readable($key) && is_readable($ca);
if (!isset($_SESSION['venture_owner_csrf'])) {
    $_SESSION['venture_owner_csrf'] = bin2hex(random_bytes(32));
}
$csrf = $_SESSION['venture_owner_csrf'];
function ventureApi(string $method, string $url, string $token, string $cert, string $key, string $ca, ?array $payload = null): array {
    $ch = curl_init($url);
    $headers = ['Authorization: Bearer '.$token, 'Accept: application/json'];
    if ($payload !== null) { $headers[]='Content-Type: application/json'; $headers[]='X-Owner-Intent: explicit'; }
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true, CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers, CURLOPT_TIMEOUT => 8,
        CURLOPT_CONNECTTIMEOUT => 4, CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_SSLCERT => $cert, CURLOPT_SSLKEY => $key, CURLOPT_CAINFO => $ca,
        CURLOPT_PROTOCOLS => CURLPROTO_HTTPS,
    ]);
    if ($payload !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload, JSON_THROW_ON_ERROR));
    $body = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return [$status, is_string($body) ? json_decode($body, true) : null];
}
$error = '';
$notice = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($csrf, (string)($_POST['csrf'] ?? ''))) {
        http_response_code(403); exit('Invalid session token');
    }
    if (!$ready) { $error = 'Owner integration is not configured.'; }
    elseif (isset($_POST['owner_password'])) {
        if (password_verify((string)$_POST['owner_password'], $hash)) {
            session_regenerate_id(true);
            $_SESSION['venture_owner_until'] = time() + 900;
        } else { $error = 'Owner verification failed.'; }
    } elseif (isset($_POST['decision']) && (int)($_SESSION['venture_owner_until'] ?? 0) > time()) {
        $decision = (string)$_POST['decision'];
        $reason = (string)($_POST['reason'] ?? '');
        $cycle = (string)($_POST['cycle_id'] ?? '');
        $digest = (string)($_POST['digest'] ?? '');
        if (!in_array($decision, ['APPROVE_FOR_RESEARCH','REJECT','REQUEST_CHANGES'], true)
            || strlen($reason) > 500 || !preg_match('/^[a-zA-Z0-9-]{1,60}$/D', $cycle)
            || !preg_match('/^[0-9a-f]{64}$/D', $digest)
            || ($decision === 'REQUEST_CHANGES' && trim($reason) === '')) {
            $error = 'Invalid decision request.';
        } else {
            [$status, $response] = ventureApi('POST', rtrim($endpoint,'/').'/v1/owner/reviews',
                $token, $cert, $key, $ca,
                ['cycle_id'=>$cycle, 'proposal_digest'=>$digest, 'decision'=>$decision, 'reason'=>$reason]);
            if ($status === 200) $notice = 'Decision recorded. This does not authorize funding or launch.';
            else $error = 'Review was not saved (stale, duplicate, or connection error).';
        }
    } else { $error = 'Owner verification required.'; }
}
$verified = $ready && (int)($_SESSION['venture_owner_until'] ?? 0) > time();
$ideas = [];
if ($verified) {
    [$status, $response] = ventureApi('GET',rtrim($endpoint,'/').'/v1/owner/ideas', $token,$cert,$key,$ca);
    if ($status === 200 && is_array($response['ideas'] ?? null)) $ideas = $response['ideas'];
    else $error = 'Unable to retrieve proposals securely.';
}
function h(mixed $v): string { return htmlspecialchars((string)$v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
?>
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Venture Management | CTKFamily</title><link rel="stylesheet" href="../css/style.css">
<style>body{font-family:system-ui,sans-serif;background:#f1f6f3;color:#17332a;margin:0}main{max-width:980px;margin:35px auto;padding:20px}.proposal{background:white;border:1px solid #d1ded5;border-radius:12px;padding:22px;margin:18px 0}dt{font-weight:700;margin-top:12px}dd{margin:4px 0 0;white-space:pre-wrap}button{background:#17613f;color:white;border:0;border-radius:8px;padding:10px;margin:8px 8px 0 0}textarea,input{max-width:100%;padding:9px}textarea{width:100%;height:65px}.error{color:#9a2335}.notice{color:#17613f}</style>
</head><body><main><p><a href="apps.php">Applications</a> / Venture Management</p><h1>Venture Ideas</h1>
<p>Review CEO proposals. Research approval never grants venture launch or financial authority.</p>
<?php if ($error !== ''): ?><p class="error" role="alert"><?=h($error)?></p><?php endif; ?>
<?php if ($notice !== ''): ?><p class="notice" role="status"><?=h($notice)?></p><?php endif; ?>
<?php if (!$ready): ?><p>Owner API configuration is pending independent security review.</p>
<?php elseif (!$verified): ?><form method="post"><input type="hidden" name="csrf" value="<?=h($csrf)?>">
<label>Owner verification <input type="password" name="owner_password" autocomplete="current-password" required></label><button type="submit">Verify Owner</button></form>
<?php else: ?>
<?php foreach ($ideas as $idea): $p=$idea['proposal'] ?? []; $review=$idea['review'] ?? null; ?>
<section class="proposal"><h2><?=h($p['title'] ?? 'Untitled venture')?></h2>
<dl><?php foreach (['customer'=>'Target customers','problem'=>'Problem','solution'=>'Solution','demand_hypothesis'=>'Demand hypothesis','acquisition_hypothesis'=>'Acquisition hypothesis','estimated_setup_usd'=>'Estimated setup (USD)','major_risk'=>'Primary risk','validation_plan'=>'Validation plan'] as $key=>$label): ?>
<dt><?=h($label)?></dt><dd><?=h($p[$key] ?? 'Not supplied')?></dd><?php endforeach; ?></dl>
<?php if ($review): ?><p><strong>Reviewed:</strong> <?=h($review['decision'] ?? '')?> (<?=h($review['reviewed_utc'] ?? '')?>)</p>
<?php else: ?><p><strong>Status:</strong> Pending Owner Review</p>
<form method="post"><input type="hidden" name="csrf" value="<?=h($csrf)?>">
<input type="hidden" name="cycle_id" value="<?=h($idea['cycle_id'] ?? '')?>">
<input type="hidden" name="digest" value="<?=h($idea['digest'] ?? '')?>">
<label>Reason or requested changes<textarea maxlength="500" name="reason"></textarea></label>
<div><button name="decision" value="APPROVE_FOR_RESEARCH">Approve for Research</button>
<button name="decision" value="REJECT">Reject</button>
<button name="decision" value="REQUEST_CHANGES">Request Changes</button></div></form><?php endif; ?>
</section><?php endforeach; ?>
<?php if (!$ideas && $error === ''): ?><p>No proposals awaiting display.</p><?php endif; ?>
<?php endif; ?></main></body></html>
