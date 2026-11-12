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
-- Esquema y datos semilla para la demostración de RLS + PgBouncer
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Funciones auxiliares que coinciden con el esquema de NEXO (sql/schema.sql líneas 1322-1345)
CREATE OR REPLACE FUNCTION get_current_school_id()
RETURNS UUID AS $$
DECLARE v_school_id TEXT;
BEGIN
    v_school_id := current_setting('app.current_school_id', true);
    IF v_school_id IS NULL OR v_school_id = '' THEN RETURN NULL; END IF;
    RETURN v_school_id::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_current_role()
RETURNS TEXT AS $$
DECLARE v_role TEXT;
BEGIN
    v_role := current_setting('app.current_role', true);
    IF v_role IS NULL OR v_role = '' THEN RETURN NULL; END IF;
    RETURN v_role;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Tabla schools
DROP TABLE IF EXISTS schools CASCADE;
CREATE TABLE schools (
    school_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_name TEXT NOT NULL
);

-- Tabla students
DROP TABLE IF EXISTS students CASCADE;
CREATE TABLE students (
    student_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id UUID NOT NULL REFERENCES schools(school_id),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL
);

-- Datos semilla de schools
INSERT INTO schools (school_id, school_name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Oakwood High School'),
    ('22222222-2222-2222-2222-222222222222', 'Pinecrest Academy');

-- Datos semilla de students (2 por escuela)
INSERT INTO students (school_id, first_name, last_name) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Alice', 'Smith'),
    ('11111111-1111-1111-1111-111111111111', 'Bob', 'Jones'),
    ('22222222-2222-2222-2222-222222222222', 'Charlie', 'Brown'),
    ('22222222-2222-2222-2222-222222222222', 'Diana', 'Prince');

-- Las políticas RLS las aplica src/rls_policies.sql (cargado por make up / montaje de compose)

-- Otorga acceso al usuario de la aplicación
GRANT ALL PRIVILEGES ON schools TO nexo_app;
GRANT ALL PRIVILEGES ON students TO nexo_app;
