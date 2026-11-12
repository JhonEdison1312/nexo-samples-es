-- AÑADIDO PARA ESTA MUESTRA
\echo 'Insertar 3 registros de auditoría...'
INSERT INTO global_audit_logs (school_id, performed_by_user_id, action_type, description, ip_address, prev_audit_id, chain_hash)
VALUES
    ('123e4567-e89b-12d3-a456-426614174000', '123e4567-e89b-12d3-a456-426614174010', 'LOGIN', 'El usuario inició sesión', '192.168.1.1', NULL, hash_hmac('sha256', 'GENESIS|123e4567-e89b-12d3-a456-426614174000|123e4567-e89b-12d3-a456-426614174010|LOGIN|User logged in|192.168.1.1|2024-01-01 00:00:00', 'demo-secret')),
    ('123e4567-e89b-12d3-a456-426614174000', '123e4567-e89b-12d3-a456-426614174010', 'UPDATE', 'El usuario actualizó su perfil', '192.168.1.1', (SELECT log_id FROM global_audit_logs WHERE action_type='LOGIN' LIMIT 1), 'PLACEHOLDER_HASH_2'),
    ('123e4567-e89b-12d3-a456-426614174000', '123e4567-e89b-12d3-a456-426614174010', 'LOGOUT', 'El usuario cerró sesión', '192.168.1.1', (SELECT log_id FROM global_audit_logs WHERE action_type='UPDATE' LIMIT 1), 'PLACEHOLDER_HASH_3');

\echo 'Verificación de la cadena: PASS (simulada: en código real se recalcularían todos los hashes)'
SELECT log_id, action_type, LEFT(chain_hash, 16) as hash_preview FROM global_audit_logs ORDER BY created_at;

\echo 'Manipulando el registro intermedio...'
UPDATE global_audit_logs SET description = 'CAMBIO MALICIOSO' WHERE action_type = 'UPDATE';

\echo 'Verificación de la cadena: FAIL - manipulación detectada (simulada)'
SELECT log_id, action_type, description FROM global_audit_logs ORDER BY created_at;
