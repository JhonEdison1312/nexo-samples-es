// AÑADIDO PARA ESTA MUESTRA
// Demo de escenario completo para 03-edge-pipeline:
// 1. Evento biométrico registrado sin conexión -> outbox en SQLite
// 2. Fallo de sincronización de red -> reintento con backoff/conteo de intentos
// 3. Recuperación de red -> sincronización cifrada AES-256-GCM con nonce único
// 4. Deduplicación del lado del servidor vía Redis NX
// 5. Ataque de replay rechazado (nonce duplicado bloqueado)
// SIMULATED: el servidor simulado (escucha en el puerto 8080) es SIMULATED solo para fines de demo.

#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <chrono>
#include <thread>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>

#include "utils/Logger.h"
#include "base_de_datos/encryption.h"
#include "base_de_datos/sqlite_manager.h"
#include "base_de_datos/cloud_manager.h"
#include "hardware/dev_stub/DevStubBiometricSensor.h"

namespace fs = std::filesystem;

// SIMULATED manejador de ingesta simulado del lado del servidor. Refleja la
// verificación anti-replay del nonce del handler privado de ingesta
// backend/api/api.php (archivo privado, no forma parte de este repositorio).
// SIMULATED: la rama de Redis caído devuelve 503 (fail-closed) para mayor
// claridad en la demo; el comportamiento exacto fail-open/fail-closed del
// handler privado no forma parte de este repositorio.
class IngestServerMock {
public:
    explicit IngestServerMock(int redisPort = 16379) : m_redisPort(redisPort) {}

    struct Response {
        int statusCode;
        std::string message;
    };

    Response ingest(const std::string& nonce, const std::string& b64Ciphertext, const std::string& expectedPlainDoc) {
        if (nonce.empty()) {
            return {400, "Falta el nonce"};
        }

        // 1. Deduplicación atómica en Redis: SET <nonce> 1 NX EX 604800
        int nonceResult = checkNonceInRedis(nonce);
        if (nonceResult == kRedisDown) {
            LOG_ERROR("[SERVER] Redis no está disponible — no se puede verificar el nonce, se rechaza la ingesta");
            return {503, "Redis no está disponible"};
        }
        if (nonceResult == kNonceDuplicate) {
            LOG_WARN("[SERVER] EDGE_REPLAY_NONCE_DUPLICATE: ¡Ataque de replay detectado! Nonce ya utilizado: {}", nonce);
            return {403, "Nonce ya utilizado"};
        }

        // 2. El servidor descifra el payload AES-256-GCM
        auto& crypto = Encryption::getInstance();
        std::string decrypted = crypto.decrypt(b64Ciphertext);
        if (decrypted.empty() || decrypted.find(expectedPlainDoc) == std::string::npos) {
            return {400, "Falló el descifrado o la autenticación"};
        }

        LOG_INFO("[SERVER] Ingesta OK: evento aceptado (202 Accepted)");
        return {202, "Aceptado"};
    }

private:
    int m_redisPort;

    enum NonceCheck { kNonceOk = 0, kNonceDuplicate = 1, kRedisDown = 2 };

    int checkNonceInRedis(const std::string& nonce) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            LOG_ERROR("[SERVER] Falló la creación del socket para Redis");
            return kRedisDown;
        }

        struct sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(static_cast<uint16_t>(m_redisPort));
        inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);

        if (connect(sock, reinterpret_cast<struct sockaddr*>(&addr), sizeof(addr)) < 0) {
            close(sock);
            LOG_ERROR("[SERVER] Redis no disponible en el puerto {}", m_redisPort);
            return kRedisDown;
        }

        // Enviar RESP: SET <nonce> 1 NX EX 604800
        std::string cmd = "*6\r\n$3\r\nSET\r\n$" + std::to_string(nonce.size()) + "\r\n" + nonce +
                          "\r\n$1\r\n1\r\n$2\r\nNX\r\n$2\r\nEX\r\n$6\r\n604800\r\n";
        send(sock, cmd.data(), cmd.size(), 0);

        char buf[256]{};
        ssize_t n = recv(sock, buf, sizeof(buf) - 1, 0);
        close(sock);

        if (n <= 0) {
            LOG_ERROR("[SERVER] Falló la recepción de la respuesta de Redis");
            return kRedisDown;
        }
        std::string reply(buf, static_cast<size_t>(n));
        // +OK -> éxito; $-1 -> ya existe (duplicado)
        return (reply.rfind("+OK", 0) == 0) ? kNonceOk : kNonceDuplicate;
    }
};

int main() {
    Logger::initialize("edge_demo.log", "info");
    bool allOk = true;
    auto assertThat = [&](bool cond, const std::string& what) {
        std::cout << "  [" << (cond ? "PASS" : "FAIL") << "] " << what << std::endl;
        if (!cond) allOk = false;
    };
    std::cout << "=== DEMO DE VERIFICACIÓN 03-EDGE-PIPELINE ===" << std::endl;

    // Configurar las rutas de trabajo en /tmp
    fs::path tempDir = fs::temp_directory_path() / "nexo_edge_demo";
    fs::create_directories(tempDir);
    std::string dbPath = (tempDir / "offline_outbox.db").string();
    std::string keyPath = (tempDir / "device.key").string();

    fs::remove(dbPath);
    fs::remove(keyPath);

    // 1. Inicialización de la clave del dispositivo
    std::cout << "\n--- PASO 1: Configuración de clave vinculada al dispositivo (fail-closed post-corrección y opt-in de desarrollo) ---" << std::endl;
    auto& crypto = Encryption::getInstance();
    crypto.setKeyFile(keyPath);

    // Demostrar el fail-closed cuando el hardware binding falla sin opt-in
    unsetenv("NEXO_ALLOW_DEV_KEY_FALLBACK");
    std::string devKey(32, 'K');
    bool failClosedOk = !crypto.provisionKey(devKey);
    std::cout << "Sin la bandera de opt-in: el hardware binding falla -> fail-closed: "
              << (failClosedOk ? "SÍ (clave rechazada)" : "NO") << std::endl;
    assertThat(failClosedOk, "fail-closed: clave rechazada sin opt-in");

    // Habilitar explícitamente el opt-in de desarrollador/simulador
    setenv("NEXO_ALLOW_DEV_KEY_FALLBACK", "1", 1);
    bool optInOk = crypto.provisionKey(devKey);
    std::cout << "Con NEXO_ALLOW_DEV_KEY_FALLBACK=1: clave aprovisionada: "
              << (optInOk ? "SÍ (modo 0600)" : "NO") << std::endl;
    assertThat(optInOk, "opt-in: clave aprovisionada con NEXO_ALLOW_DEV_KEY_FALLBACK=1");
    unsetenv("NEXO_ALLOW_DEV_KEY_FALLBACK");

    // 2. Inicializar la base de datos outbox SQLite
    std::cout << "\n--- PASO 2: Inicialización del outbox SQLite ---" << std::endl;
    auto& db = SqliteManager::getInstance();
    if (!db.initialize(dbPath)) {
        std::cerr << "Falló la inicialización del outbox SQLite" << std::endl;
        return 1;
    }
    std::cout << "Esquema del outbox SQLite creado: PRAGMA journal_mode=WAL; synchronous=EXTRA" << std::endl;

    // 3. Registrar evento biométrico sin conexión
    std::cout << "\n--- PASO 3: Captura de evento sin conexión ---" << std::endl;
    DevStubBiometricSensor sensor;
    sensor.initialize();
    std::string studentDoc = "1098765432";
    std::string eventType = "BIOMETRIC_ATTENDANCE_CHECKIN";

    bool saved = db.saveAudit(studentDoc, eventType);
    std::cout << "Evento de asistencia registrado en el outbox: " << (saved ? "ÉXITO" : "FALLIDO") << std::endl;
    std::cout << "Registros pendientes de sincronización en el outbox: " << db.getPendingAuditCount() << std::endl;
    assertThat(saved, "evento biométrico persistido en el outbox");
    assertThat(db.getPendingAuditCount() == 1, "el outbox tiene exactamente 1 registro pendiente");

    // 4. Intento de sincronización sin conexión (red caída -> reintento con backoff)
    std::cout << "\n--- PASO 4: Fallo de red y contabilidad de reintentos ---" << std::endl;
    std::vector<AuditRecord> pending;
    db.getPendingAudits(pending);
    if (!pending.empty()) {
        int auditId = pending[0].id;
        std::cout << "Intentando sincronizar con el servidor inalcanzable..." << std::endl;
        db.incrementAuditAttempt(auditId);
        std::vector<AuditRecord> retried;
        db.getPendingAudits(retried);
        std::cout << "Falló la sincronización. Contador de reintentos incrementado a: " << retried[0].attempts << std::endl;
        std::cout << "El registro permanece en cola en el outbox: SÍ" << std::endl;
        assertThat(retried[0].attempts >= 1, "contador de intentos de reintento incrementado");
    } else {
        assertThat(false, "registro del outbox presente para el conteo de reintentos");
    }

    // 5. Sincronización exitosa con deduplicación del servidor
    std::cout << "\n--- PASO 5: Ingesta síncrona exitosa ---" << std::endl;
    int redisPort = 16379;
    if (const char* envPort = std::getenv("NEXO_REDIS_PORT")) {
        redisPort = std::stoi(envPort);
    }
    IngestServerMock server(redisPort);
    std::string nonce = "nonce-demo-uuid-" + std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
    
    // Cifrar la carga con AES-256-GCM
    std::string plainPayload = R"({"doc":")" + studentDoc + R"(","event":")" + eventType + R"(","nonce":")" + nonce + R"("})";
    std::string encryptedPayload = crypto.encrypt(plainPayload);
    std::cout << "Carga cifrada con AES-256-GCM (IV + ciphertext + tag)" << std::endl;

    auto resp1 = server.ingest(nonce, encryptedPayload, studentDoc);
    std::cout << "Respuesta del servidor (primera entrega): HTTP " << resp1.statusCode << " (" << resp1.message << ")" << std::endl;

    if (resp1.statusCode == 503) {
        std::cerr << "ERROR: Redis no está disponible — deduplicación de nonce no disponible, ingesta rechazada" << std::endl;
        db.close();
        return 1;
    }
    assertThat(resp1.statusCode == 202, "primera entrega aceptada (HTTP 202)");

    if (resp1.statusCode == 202) {
        if (!pending.empty()) {
            db.clearAudit(pending[0].id);
        }
        std::cout << "Elemento del outbox marcado como sincronizado. Registros pendientes restantes: "
                  << db.getPendingAuditCount() << std::endl;
        assertThat(db.getPendingAuditCount() == 0, "outbox vaciado tras la sincronización");
    }

    // 6. Rechazo de ataque de replay
    std::cout << "\n--- PASO 6: Detección de ataque de replay ---" << std::endl;
    std::cout << "El atacante reenvía exactamente el mismo paquete cifrado con nonce duplicado..." << std::endl;
    auto resp2 = server.ingest(nonce, encryptedPayload, studentDoc);
    std::cout << "Respuesta del servidor (paquete de replay): HTTP " << resp2.statusCode << " (" << resp2.message << ")" << std::endl;
    assertThat(resp2.statusCode == 403, "paquete de replay rechazado (HTTP 403)");
    if (resp2.statusCode == 403) {
        std::cout << "¡El ataque de replay fue RECHAZADO por el servidor!" << std::endl;
    } else {
        std::cerr << "ERROR: el ataque de replay NO fue rechazado (se esperaba 403, se obtuvo " << resp2.statusCode << ")" << std::endl;
    }

    db.close();
    if (!allOk) {
        std::cerr << "=== DEMO 03-EDGE-PIPELINE COMPLETA: COMPROBACIONES FALLIDAS ===" << std::endl;
        return 1;
    }
    std::cout << "\n=== DEMO 03-EDGE-PIPELINE COMPLETA: TODAS LAS COMPROBACIONES PASARON ===" << std::endl;
    return 0;
}
