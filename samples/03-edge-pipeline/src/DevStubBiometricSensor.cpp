/**
 * =============================================================================
 * DevStubBiometricSensor.cpp — Implementación stub del sensor biométrico.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Simula un sensor biométrico para pruebas sin hardware. Inicialización
 *   inmediata, el registro devuelve una plantilla dummy y la búsqueda simula
 *   una coincidencia cada 5 intentos con un retardo de 500 ms.
 */

#include "hardware/dev_stub/DevStubBiometricSensor.h"
#include "utils/Logger.h"
#include <thread>
#include <chrono>

NexoResult<void> DevStubBiometricSensor::initialize() {
    LOG_INFO("[STUB] Sensor biométrico inicializado (dev-stub)");
    m_ready = true;
    return NexoResult<void>::success();
}

NexoResult<void> DevStubBiometricSensor::enrollUser(uint32_t userId, std::vector<uint8_t>& templateOut) {
    if (!m_ready) return NexoResult<void>::fail(NexoError::NotInitialized, "Sensor no inicializado");
    LOG_INFO("[STUB] Registrar usuario ID={}", userId);
    templateOut.assign(256, 0xAA);
    return NexoResult<void>::success();
}

NexoResult<void> DevStubBiometricSensor::searchUser(const std::vector<uint8_t>& /*templateData*/,
                                                     uint32_t& matchedUserId, float& matchScore) {
    if (!m_ready) return NexoResult<void>::fail(NexoError::NotInitialized, "Sensor no inicializado");

    // Retardo realista para simular el procesamiento del sensor
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // Simular que normalmente no hay huella presente (1 coincidencia de cada 5 intentos)
    static int count = 0;
    if (++count % 5 == 0) {
        LOG_DEBUG("[STUB] Buscar usuario (coincidencia simulada ID=1)");
        matchedUserId = 1;
        matchScore = 95.0f;
        return NexoResult<void>::success();
    }

    LOG_DEBUG("[STUB] Buscar usuario (sin coincidencia - stub)");
    return NexoResult<void>::fail(NexoError::NoMatch, "Sin coincidencia (stub)");
}

NexoResult<void> DevStubBiometricSensor::deleteUser(uint32_t userId) {
    if (!m_ready) return NexoResult<void>::fail(NexoError::NotInitialized, "Sensor no inicializado");
    LOG_INFO("[STUB] Eliminar usuario ID={}", userId);
    return NexoResult<void>::success();
}

