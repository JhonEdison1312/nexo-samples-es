#pragma once
#include "hal/INotification.h"

/**
 * =============================================================================
 * DevStubNotification.h — Implementación stub de notificaciones.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Implementación de INotification que emite logs de pitidos en lugar de
 *   accionar GPIO, zumbador o LEDs reales. Usada en modo de desarrollo.
 */
class DevStubNotification : public INotification {
public:
    void notifySuccess() override;
    void notifyError() override;
    void notifyWarning() override;
};

