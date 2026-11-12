#pragma once
#include <string>
#include <vector>
#include <cstdint>
#include <sqlite3.h>

/**
 * =============================================================================
 * sqlite_manager.h — Interfaz singleton de la base de datos local SQLite.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Contiene el almacenamiento local del dispositivo edge: estudiantes,
 *   patrones de asistencia, inasistencias (heredado), audit_trail para
 *   subidas pendientes y una tabla config (clave/valor). Todas las
 *   plantillas de huella se cifran con Encryption antes de almacenarse y se
 *   descifran al leerse.
 *
 * TABLAS:
 *   - estudiantes: documento (PK), nombre, nombre/teléfono del acudiente,
 *     huella_id, template_huella (base64 cifrado).
 *   - patrones: resumen de llegadas tempranas/tardías por estudiante.
 *   - inasistencias: heredado (no implementado en el cpp).
 *   - audit_trail: eventos locales pendientes de sincronización con la nube.
 *   - config: pares clave/valor (clave AES, token, etc.).
 *
 * DEPENDENCIAS:
 *   - sqlite3
 *   - base_de_datos/encryption.h (cifrado de templates)
 *   - openssl/rand.h (IV aleatorio para templates)
 */
struct Estudiante {
    std::string documento;
    std::string nombre;
    std::string telefono_acudiente;
    std::string nombre_acudiente;
    uint32_t huella_id = 0;
    std::vector<uint8_t> template_huella;
    std::string school_id;  // Multi-inquilino: identificador de la institución
};

struct AuditRecord {
    int id;
    std::string documento;
    std::string event;
    int timestamp;
    int attempts;
};

class SqliteManager {
public:
    static SqliteManager& getInstance() {
        static SqliteManager instance;
        return instance;
    }

    bool initialize(const std::string& dbPath = "nexo_edge.db");
    void close();
    bool factoryReset();

    // Estudiantes
    bool saveEstudiante(const Estudiante& est);
    bool getEstudianteByDocumento(const std::string& doc, Estudiante& est);
    bool getEstudianteByHuellaID(uint32_t huellaId, Estudiante& est);
    bool deleteEstudiante(const std::string& doc);
    uint32_t getNextHuellaID();

    // Multi-huella (hasta 2 dedos por estudiante)
    bool saveHuella(const std::string& doc, int fingerSlot, uint32_t huellaId,
                    const std::vector<uint8_t>& tpl, const std::string& schoolId);
    int  getHuellaCount(const std::string& doc);
    bool getHuellaIdsByDocumento(const std::string& doc, std::vector<uint32_t>& idsOut);
    bool huellaSlotExists(const std::string& doc, int fingerSlot);

    // Patrones de asistencia (UPSERT)
    bool updatePattern(const std::string& documento, bool temprano, bool tarde);
    bool getPatternSummary(const std::string& documento, int& temprano, int& tarde, int& total);

    // PAE
    bool savePAE(const std::string& documento, bool recibido);

    // Seguimiento de inasistencias
    bool checkInasistencia(const std::string& documento);
    bool deleteInasistencia(const std::string& documento);

    // Registro de auditoría
    bool saveAudit(const std::string& documento, const std::string& event);
    bool getPendingAudits(std::vector<AuditRecord>& audits);
    bool clearAudit(int id);
    bool clearAudit(const std::string& documento, const std::string& event); // Se conserva por compatibilidad
    bool incrementAuditAttempt(int id);
    bool markAuditError(int id);
    // Purgar registros antiguos sincronizados o en DLQ para evitar llenar la tarjeta SD
    int purgeOldAuditTrail(int daysSynced = 30, int daysDlq = 90);
    // Métricas de la cola para telemetría
    int getPendingAuditCount();
    int getDlqCount();
    // Reencolado a largo plazo — reactiva registros synced=-1 (SyncWorker, ~1h)
    int requeueDlqItems(int limit = 20);
    // VACUUM para recuperar espacio físico tras la purga
    bool vacuum();

    // Carga masiva para la caché biométrica
    bool getAllEstudiantesConTemplate(std::vector<Estudiante>& estudiantes);

    // Almacén KV de configuración
    bool setConfig(const std::string& key, const std::string& value);
    std::string getConfig(const std::string& key, const std::string& defaultVal = "");

    sqlite3* getDB() { return db; }

private:
    SqliteManager() = default;
    ~SqliteManager() { close(); }
    sqlite3* db = nullptr;
    bool createTables();
    void migrateSchema();  // Migraciones para bases de datos existentes
};

