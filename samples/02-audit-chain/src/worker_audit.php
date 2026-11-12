/**
 * Calcula el HMAC-SHA256 que vincula un registro con el anterior de la cadena.
 *
 * @param string|null $prevHash Hash del registro anterior.
 * @param string|null $schoolId UUID de la escuela.
 * @param string|null $actorId UUID del actor.
 * @param string $eventType Tipo de evento.
 * @param string $description Descripción.
 * @param string $ipAddress Dirección IP.
 * @param string $createdAt Marca de tiempo.
 * @param string $secret Secreto HMAC.
 * @return string Hash HMAC-SHA256.
 */
function calculateAuditHash($prevHash, $schoolId, $actorId, $eventType, $description, $ipAddress, $createdAt, $secret) {
    $prevHash = $prevHash ?: 'GENESIS';
    $schoolId = $schoolId ?: 'NULL';
    $actorId = $actorId ?: 'NULL';
    $payload = "{$prevHash}|{$schoolId}|{$actorId}|{$eventType}|{$description}|{$ipAddress}|{$createdAt}";
    return hash_hmac('sha256', $payload, $secret);
}

/**
 * Inserta un lote de registros de auditoría en una transacción manteniendo la cadena de hashes.
 *
 * @param PDO $conn Conexión PDO.
 * @param array $rows Filas decodificadas desde Redis.
 * @return void
 *
 * Efectos secundarios: inicia y confirma/revierte una transacción; en caso
 * de error, vuelve a encolar las filas fallidas en `queue:audit_logs`.
 */
function insertBatch($conn, array $rows) {
    if (empty($rows)) return;
    
    $secret = getenv('APP_NEXO_HMAC_SECRET');
    if (!$secret || $secret === 'default-secret-change-me') {
        error_log('[AUDIT_WORKER] FATAL: APP_NEXO_HMAC_SECRET no está configurado o tiene el valor por defecto. El worker no puede iniciarse.');
        exit(1);
    }
    $lastHashes = []; // Caché en memoria para el lote

    $conn->beginTransaction();
    // El trigger de la cadena requiere el GUC dentro de la transacción
    // (el modo transacción de Supavisor descarta los de nivel de sesión).
    if (function_exists('nxDbSetHmac')) nxDbSetHmac($conn);
    try {
        $stmt = $conn->prepare("
            INSERT INTO global_audit_logs
                (log_id, school_id, performed_by_user_id, action_type,
                 description, ip_address, action_details, created_at,
                 prev_audit_id, chain_hash)
            VALUES
                (?, ?, ?, ?, ?,
                 ?::inet,
                 ?::jsonb,
                 ?, ?, ?)
        ");
        
        foreach ($rows as $row) {
            $schoolId = $row['school_id'];

            // RLS: gal_insert/gal_select requieren school_id = contexto — se
            // establece por escuela dentro de la transacción (set_config true
            // equivale a SET LOCAL). El rol permite insertar eventos de
            // sistema sin escuela (pre-auth: LOGIN_*, etc.); school_id delimita
            // lo que es legible.
            if (!($ctxSet ?? false)) {
                $conn->exec("SELECT set_config('app.current_role', 'SYSTEM_WORKER', true)");
                $ctxSet = true;
            }
            if (($lastCtx ?? null) !== $schoolId) {
                if ($schoolId === null) {
                    $conn->exec("SELECT set_config('app.current_school_id', '', true)");
                } else {
                    $conn->exec("SELECT set_config('app.current_school_id', " . $conn->quote((string)$schoolId) . ", true)");
                }
                $lastCtx = $schoolId;
            }

            if (!isset($lastHashes[$schoolId])) {
                $chk = $conn->prepare("SELECT log_id, chain_hash FROM global_audit_logs WHERE school_id = ? ORDER BY created_at DESC, log_id DESC LIMIT 1");
                $chk->execute([$schoolId]);
                $lastHashes[$schoolId] = $chk->fetch(PDO::FETCH_ASSOC) ?: ['log_id' => null, 'chain_hash' => 'GENESIS'];
            }
            
            $prevAuditId = $lastHashes[$schoolId]['log_id'];
            $prevHash = $lastHashes[$schoolId]['chain_hash'];
            
            $logId = generateUuidV4();
            $actorId = $row['actor_id'];
            $eventType = $row['event_type'];
            $description = $row['description'];
            $ipAddress = $row['ip_address'] ?? '0.0.0.0';
            
            // Formato para coincidir con el estilo del cast jsonb::text de PostgreSQL
            $uriStr = isset($row['uri']) ? '"' . str_replace('"', '\"', $row['uri']) . '"' : '"N/A"';
            $reqStr = isset($row['request_id']) ? '"' . str_replace('"', '\"', $row['request_id']) . '"' : 'null';
            $actionDetailsJson = '{"uri": ' . $uriStr . ', "request_id": ' . $reqStr . '}';
            
            // Formato para coincidir con el estilo del cast timestamptz de PostgreSQL (YYYY-MM-DD HH:MM:SS+00)
            $createdAt = $row['created_at'] ?? gmdate('Y-m-d H:i:s');
            $createdAtPg = date('Y-m-d H:i:s+00', strtotime($createdAt));

            $hash = calculateAuditHash($prevHash, $schoolId, $actorId, $eventType, $actionDetailsJson, $ipAddress, $createdAtPg, $secret);

            $stmt->execute([
                $logId,
                $schoolId,
                $actorId,
                $eventType,
                $description,
                $ipAddress,
                $actionDetailsJson,
                $createdAt,
                $prevAuditId,
                $hash
            ]);
            
            // Actualiza la caché del lote para el siguiente registro
            $lastHashes[$schoolId] = ['log_id' => $logId, 'chain_hash' => $hash];
        }
