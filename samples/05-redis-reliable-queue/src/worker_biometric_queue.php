// ============================================================
// Cola confiable: LMOVE mueve atómicamente ingest -> processing
// ============================================================

// Script Lua atómico que hace LMOVE + inyecta el timestamp.
// Esto garantiza que, si el worker muere, el GC pueda medir cuánto tiempo
// lleva el elemento en processing y reinsertarlo.
$scriptReliablePop = <<<'LUA'
local ingest = KEYS[1]
local processing = KEYS[2]
local now = tonumber(ARGV[1])
local item = redis.call('LMOVE', ingest, processing, 'RIGHT', 'LEFT')
if item then
    local ok, job = pcall(cjson.decode, item)
    if ok and job then
        job.processing_since = now
        local newItem = cjson.encode(job)
        redis.call('LREM', processing, 0, item)
        redis.call('LPUSH', processing, newItem)
        return newItem
    end
    return item
end
return nil
LUA;

// Garbage Collector — reencola los jobs zombie en ingest
// (más de 5 minutos en processing sin commit exitoso).
$scriptGc = <<<'LUA'
local processing = KEYS[1]
local ingest = KEYS[2]
local maxAge = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local items = redis.call('LRANGE', processing, 0, -1)
local recovered = 0
for i = 1, #items do
    local item = items[i]
    local ok, job = pcall(cjson.decode, item)
    if ok and job and job.processing_since then
        if (now - job.processing_since) > maxAge then
            redis.call('LREM', processing, 0, item)
            redis.call('LPUSH', ingest, item)
            recovered = recovered + 1
        end
    else
        redis.call('LREM', processing, 0, item)
        redis.call('LPUSH', ingest, item)
        recovered = recovered + 1
    end
end
return recovered
LUA;

$GC_MAX_AGE_SEC = (int)(getenv('BIOMETRIC_GC_MAX_AGE') ?: 300);
$EMPTY_QUEUE_SLEEP_US = (int)(getenv('BIOMETRIC_EMPTY_QUEUE_SLEEP_US') ?: 1_000_000); // 1s por defecto (evita 20 polls/s en Upstash)

logW('START', 'Worker biométrico asíncrono iniciado');
$redis = null;
try {
    $redis = getRedisConnection(true);
} catch (Exception $e) {}

$iterations = 0;
$lastGc = 0;
$lastHeartbeat = 0;
$lastOutboxDrain = 0;

// D-1: drena ingest_outbox — la API escribe el job durable en la misma tx que
// el evento cuando Redis falla; aquí corre el pipeline completo aunque Redis
// siga caído (PG directo). Claims con SKIP LOCKED, procesa con processJob
// (que maneja su propia tx) y marca DONE; PROCESSING antiguo vuelve a PENDING.
function drainOutbox(PDO $conn): int {
    $done = 0;
    try {
        $conn->exec("BEGIN");
        $conn->exec("SELECT set_config('app.current_role', 'SYSTEM_WORKER', true)");
        // Reencolar claims huérfanos (>5 min en PROCESSING = el worker murió)
        $conn->exec("UPDATE ingest_outbox SET status='PENDING' WHERE status='PROCESSING' AND processed_at IS NULL AND created_at < NOW() - INTERVAL '5 minutes'");
        $rows = $conn->query(
            "SELECT outbox_id, payload FROM ingest_outbox
             WHERE status='PENDING' ORDER BY created_at
             FOR UPDATE SKIP LOCKED LIMIT 10"
        )->fetchAll(PDO::FETCH_ASSOC);
        $ids = array_map(fn($r) => $r['outbox_id'], $rows);
        if ($ids) {
            $in = implode(',', array_map(fn($id) => $conn->quote($id), $ids));
            $conn->exec("UPDATE ingest_outbox SET status='PROCESSING', attempts=attempts+1 WHERE outbox_id IN ($in)");
        }
        $conn->exec("COMMIT");
    } catch (Throwable $e) {
        try { $conn->exec("ROLLBACK"); } catch (Throwable $i) {}
        logW('OUTBOX_CLAIM_ERR', $e->getMessage());
        return 0;
    }
    foreach ($rows as $r) {
        $job = json_decode($r['payload'], true);
        $ok = false;
        if ($job) {
            try { $ok = processBiometricJob($job, $conn); }
            catch (Throwable $e) { logW('OUTBOX_JOB_ERR', $e->getMessage()); }
        }
        try {
            $conn->exec("BEGIN");
            $conn->exec("SELECT set_config('app.current_role', 'SYSTEM_WORKER', true)");
            if ($ok) {
                $conn->prepare("UPDATE ingest_outbox SET status='DONE', processed_at=NOW() WHERE outbox_id=?")
                     ->execute([$r['outbox_id']]);
            } else {
                // Tras 5 intentos pasa a DLQ implícita (FAILED queda visible)
                $conn->prepare("UPDATE ingest_outbox SET status = CASE WHEN attempts >= 5 THEN 'FAILED' ELSE 'PENDING' END WHERE outbox_id=?")
                     ->execute([$r['outbox_id']]);
            }
            $conn->exec("COMMIT");
        } catch (Throwable $e) {
            try { $conn->exec("ROLLBACK"); } catch (Throwable $i) {}
        }
        if ($ok) $done++;
    }
    return $done;
}

// Guarda de ejecución: incluir el archivo (sondas/tests) no lanza el daemon.
if (realpath((string)($_SERVER['SCRIPT_FILENAME'] ?? '')) === __FILE__) {
while (!$shutdown) {
    try {
        // D-1: drenar el outbox durable cada ~15s (o en cada idle de Redis)
        if (time() - $lastOutboxDrain >= 15) {
            $lastOutboxDrain = time();
            try { drainOutbox($pdo); } catch (Throwable $e) { logW('OUTBOX_DRAIN_ERR', $e->getMessage()); }
        }

        if (!$redis) {
            sleep(15);
            try { $redis = getRedisConnection(true); } catch (Exception $e) {}
            if (!$redis) continue;
        }

        // Heartbeat cada 30 segundos
        if (time() - $lastHeartbeat >= 30) {
            $lastHeartbeat = time();
            try { sendHeartbeat($redis); } catch (Exception $e) {}
        }

        // Pop atómico con Lua + inyección de timestamp.
        $item = false;
        try {
            $item = $redis->eval($scriptReliablePop, ['queue:biometric_ingest', 'queue:biometric_processing', time()], 2);
        } catch (Exception $e) {
            logW('REDIS_ERR', $e->getMessage());
            $redis = null; // Forzar reconexión en la siguiente iteración
            @touch('/tmp/redis_circuit_open'); // Activar el circuit breaker manualmente
            continue;
        }
        if (!$item) { usleep($EMPTY_QUEUE_SLEEP_US); continue; }

        $job = json_decode($item, true);
        if (!$job) {
            try { $redis->lRem('queue:biometric_processing', $item, 0); } catch (Exception $e) {}
            continue;
        }

        try {
            $ok = processBiometricJob($job, $pdo);
            if ($ok) {
                // SOLO eliminar de processing DESPUÉS del commit() exitoso
                $redis->lRem('queue:biometric_processing', $item, 0);
                logW('OK', sprintf("action=%s req=%s", $job['action'] ?? '?', $job['request_id'] ?? 'n/a'));
            } else {
                // Fallo de lógica: reencolar en la cola principal para reintentar (igual que la excepción de BD)
                $redis->lPush('queue:biometric_ingest', $item);
                $redis->lRem('queue:biometric_processing', $item, 0);
                logW('LOGIC_FAIL', sprintf("action=%s, reencolado", $job['action'] ?? '?'));
            }
        } catch (Exception $e) {
            logW('ERR', $e->getMessage());
            $jobArray = json_decode($item, true) ?: [];
            $retries = ($jobArray['retries'] ?? 0) + 1;
            $jobArray['retries'] = $retries;

            if ($retries <= 3) {
                $redis->rPush('queue:biometric_ingest', json_encode($jobArray, JSON_UNESCAPED_UNICODE));
            } else {
                $redis->rPush('queue:biometric_dlq', json_encode($jobArray, JSON_UNESCAPED_UNICODE));
            }
            $redis->lRem('queue:biometric_processing', $item, 0);
            
            // Reconectar PDO si falló (db.php recrea el $pdo global)
            if (strpos($e->getMessage(), 'server closed the connection') !== false || strpos($e->getMessage(), 'gone away') !== false) {
                require __DIR__ . '/../core/db.php';
            }
        }
    } catch (Exception $e) {
        logW('FATAL', $e->getMessage());
        sleep(15);
        $redis = null; // Forzar reconexión
    }

    // GC de zombies cada 60 segundos.
    if (time() - $lastGc >= 60) {
        $lastGc = time();
        try {
            $recovered = $redis->eval($scriptGc, ['queue:biometric_processing', 'queue:biometric_ingest', $GC_MAX_AGE_SEC, time()], 2);
            if ($recovered > 0) {
                logW('GC_ZOMBIE', "Recuperados {$recovered} job(s) zombie tras {$GC_MAX_AGE_SEC}s");
            }
        } catch (Exception $e) {
            logW('GC_ERR', $e->getMessage());
        }
    }

    if (++$iterations % 1000 === 0) {
        gc_collect_cycles();
        $mem = memory_get_peak_usage(true) / 1024 / 1024;
        if ($mem > 256) { logW('MEM', "{$mem}MB > 256MB reinicio"); exit(0); }
    }
}
logW('STOP', 'Worker biométrico detenido'); exit(0);
}


