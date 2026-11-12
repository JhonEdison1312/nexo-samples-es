#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include "utils/NexoResult.h"

/**
 * =============================================================================
 * IBiometricSensor.h — Interfaz abstracta del sensor biométrico.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Define el contrato que debe cumplir cualquier sensor biométrico (real o
 *   stub): inicialización, registro, búsqueda 1:N, eliminación de usuario y
 *   consulta de estado. Permite inyectar implementaciones DevStub o ZK9500
 *   sin tocar main.cpp.
 *
 * FLUJO:
 *   initialize() -> isReady()
 *        │
 *        ├── enrollUser(userId, templateOut) -> almacenar plantilla cifrada
 *        └── searchUser(templateData, matchedUserId, matchScore) -> identificar
 *
 * IMPLEMENTACIONES:
 *   - hardware/dev_stub/DevStubBiometricSensor : simulation without hardware.
 *   - hardware/real/Zk9500BiometricSensor      : ZKTeco ZK9500 sensor.
 */
class IBiometricSensor {
public:
    virtual ~IBiometricSensor() = default;

    virtual NexoResult<void> initialize() = 0;

    virtual NexoResult<void> enrollUser(uint32_t userId, std::vector<uint8_t>& templateOut) = 0;

    // Añade una plantilla ya generada a la caché del sensor. Permite el registro
    // atómico: SQLite primero, caché después. Implementación no-op por defecto para stubs.
    virtual NexoResult<void> addTemplate(uint32_t userId, const std::vector<uint8_t>& templateData) {
        (void)userId;
        (void)templateData;
        return NexoResult<void>::success();
    }

    virtual NexoResult<void> searchUser(const std::vector<uint8_t>& templateData,
                                        uint32_t& matchedUserId,
                                        float& matchScore) = 0;

    virtual NexoResult<void> deleteUser(uint32_t userId) = 0;

    // Cancela una captura bloqueante (p. ej. dpfpdd_cancel). No-op por defecto.
    virtual void cancelCapture() {}

    virtual bool isReady() const = 0;
    virtual std::string getLastError() const = 0;
};

