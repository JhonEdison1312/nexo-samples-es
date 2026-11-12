#pragma once

/**
 * =============================================================================
 * INotification.h — Interfaz abstracta de notificación sonora/visual.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Contrato para emitir señales de éxito, error o advertencia. Permite
 *   implementaciones stub o reales con GPIO/zumbador/LEDs
 *   (RealGpioManager).
 */
class INotification {
public:
    virtual ~INotification() = default;
    virtual void notifySuccess() = 0;
    virtual void notifyError() = 0;
    virtual void notifyWarning() = 0;

    // Patrón de luz/sonido para el estado de alimentación del nodo.
    // state: 0=MAINS, 1=BATTERY, 2=LOW_BATTERY, 3=CRITICAL (orden de PowerState).
    virtual void notifyPowerState(int /*state*/) {}

    // Control activo del ventilador (GPIO fan). No-op en los stubs.
    virtual void setFan(bool /*on*/) {}
};

