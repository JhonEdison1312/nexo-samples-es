#pragma once

/**
 * =============================================================================
 * BiometricLockout.h — Bloqueo anti-spoof por software (G-2).
 * =============================================================================
 * RESPONSABILIDAD:
 *   Cuenta las presentaciones de dedo rechazadas (huella capturada sin
 *   coincidencia — NexoError::NoMatch en ambos sensores) sobre una ventana
 *   deslizante. Superado el umbral impone un enfriamiento durante el cual el
 *   bucle de asistencia no consulta el sensor. Retarda la adivinación de
 *   plantillas y los dedos falsos sin depender del anti-spoof del hardware.
 *
 *   El reloj se inyecta como parámetro para que las pruebas puedan avanzar
 *   el tiempo sin sleeps. No tiene estado en disco: tras un reinicio el
 *   contador vuelve a cero — el bloqueo es una defensa de ritmo, no una
 *   sanción persistente.
 */
#include <chrono>

class BiometricLockout {
public:
    using Clock = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;

    BiometricLockout(int maxFails = 8, int windowSec = 120, int cooldownSec = 60)
        : m_maxFails(maxFails), m_window(windowSec), m_cooldown(cooldownSec) {}

    // Registra un dedo rechazado. Devuelve true solo en el intento que cruza
    // el umbral (punto único para auditar/alertar). Los rechazos durante el
    // bloqueo ni lo extienden ni lo re-disparan.
    bool registerFailure(TimePoint now) {
        if (isLocked(now)) return false;
        if (now - m_windowStart > m_window) {
            m_windowStart = now;
            m_fails = 0;
        }
        if (++m_fails >= m_maxFails) {
            m_lockedUntil = now + m_cooldown;
            m_fails = 0;
            m_windowStart = now;
            return true;
        }
        return false;
    }

    // Una coincidencia válida reinicia la ventana — el uso normal nunca acumula.
    void registerSuccess(TimePoint now) {
        m_fails = 0;
        m_windowStart = now;
    }

    bool isLocked(TimePoint now) const { return now < m_lockedUntil; }

    int cooldownRemainingSec(TimePoint now) const {
        auto rem = std::chrono::duration_cast<std::chrono::seconds>(m_lockedUntil - now).count();
        return rem > 0 ? static_cast<int>(rem) : 0;
    }

    int failures() const { return m_fails; }

private:
    int m_maxFails;
    std::chrono::seconds m_window;
    std::chrono::seconds m_cooldown;
    int m_fails = 0;
    TimePoint m_windowStart{};
    TimePoint m_lockedUntil{};
};

