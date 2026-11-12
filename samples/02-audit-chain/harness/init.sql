-- AÑADIDO PARA ESTA MUESTRA
-- nexo_admin es el superusuario del docker-entrypoint; nexo_app es el
-- rol de aplicación sin privilegios con el que se conectan las pruebas.
-- Cifrado de contraseña md5 para que PgBouncer (userlist en texto plano)
-- pueda autenticarse en PostgreSQL 15+, que usa SCRAM-SHA-256 por defecto.
SET password_encryption = 'md5';
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nexo_app') THEN
        CREATE ROLE nexo_app LOGIN PASSWORD 'nexo_secret' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;
-- Esquema de base de datos para la demostración de la cadena de auditoría HMAC
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DROP TABLE IF EXISTS global_audit_logs CASCADE;
CREATE TABLE global_audit_logs (
    log_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id           UUID,
    performed_by_user_id UUID,
    action_type         VARCHAR(120) NOT NULL,
    entity_type         VARCHAR(120),
    entity_id           UUID,
    action_details      JSONB,
    ip_address          INET,
    user_agent          TEXT,
    chain_hash          TEXT,
    prev_audit_id       UUID,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Concede privilegios al usuario de la aplicación y establece la propiedad para que la prueba pueda desactivar los disparadores
ALTER TABLE global_audit_logs OWNER TO nexo_app;
GRANT ALL PRIVILEGES ON global_audit_logs TO nexo_app;
