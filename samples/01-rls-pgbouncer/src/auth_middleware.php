        try {
            $claims = verifyJwtToken($token);

            // PgBouncer: en transaction-pool mode, set_config(..., false)
            // does not persist between queries. We use beginTransaction() + SET LOCAL
            // (equivalent to set_config(..., true)) so RLS works.
            // SET LOCAL via exec() avoids EMULATE_PREPARES issues.
            $startedTx = false;
            if (!$conn->inTransaction()) {
                $conn->beginTransaction();
                $startedTx = true;
            }

            // SEC-2: problema del huevo y la gallina bajo RLS — la búsqueda
            // del usuario ya está aislada por escuela, así que el contexto se
            // establece ANTES a partir de los claims del JWT (firmados por el
            // servidor) y se vuelve a establecer DESPUÉS desde la fila de la
            // BD (autoridad final si el usuario cambió de escuela/rol desde
            // que se emitió el token).
            if (!empty($claims['school_id'])) {
                $conn->exec("SELECT set_config('app.current_school_id', " . $conn->quote((string)$claims['school_id']) . ", true)");
            }
            if (!empty($claims['role'])) {
                $conn->exec("SELECT set_config('app.current_role', " . $conn->quote(strtoupper(trim((string)$claims['role']))) . ", true)");
            }

            $stmt = $conn->prepare("
                WITH u AS (
                    SELECT u.user_id, u.email, u.first_name, u.last_name, (u.deleted_at IS NULL) AS active,
                           u.profile_photo_url, u.work_shift, u.terms_version,
                           u.role_id, r.role_name, s.school_id, s.school_name
                    FROM users u
                    INNER JOIN roles r ON u.role_id = r.role_id
                    INNER JOIN schools s ON u.school_id = s.school_id
                    WHERE u.user_id = ? AND u.deleted_at IS NULL
                    LIMIT 1
                )
                SELECT u.* FROM u
            ");
            $stmt->execute([$claims['sub']]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);

            if (!$user) {
                if ($startedTx) { try { $conn->rollBack(); } catch (Exception $ignore) {} }
                http_response_code(401);
                exit(json_encode(['status' => 'error', 'message' => 'Usuario no encontrado o inactivo']));
            }

            $roleName = strtoupper(trim($user['role_name']));
            if (is_array($allowedRoles) && !in_array($roleName, $allowedRoles, true)) {
                if ($startedTx) { try { $conn->rollBack(); } catch (Exception $ignore) {} }
                http_response_code(403);
                exit(json_encode(['status' => 'error', 'message' => 'Acceso restringido']));
            }

            // Re-set context from the DB row (authority — the JWT may
            // predate a school or role change).
            $conn->exec("SELECT set_config('app.current_school_id', " . $conn->quote((string)$user['school_id']) . ", true)");
            $conn->exec("SELECT set_config('app.current_role', " . $conn->quote($roleName) . ", true)");
            // The audit chain requires this per-tx GUC: the
            // Supabase pooler (transaction mode) discards session-level ones.
            if (function_exists('nxDbSetHmac')) nxDbSetHmac($conn);
