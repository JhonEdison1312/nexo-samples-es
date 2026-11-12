#pragma once
#include "hal/IHttpClient.h"

/**
 * =============================================================================
 * DevStubHttpClient.h — Implementación stub del cliente HTTP.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Implementación de IHttpClient que simula una respuesta HTTP exitosa
 *   sin ninguna conexión de red. Permite probar CloudManager sin conexión.
 */
class DevStubHttpClient : public IHttpClient {
public:
    bool postRequest(const std::string& url,
                     const std::string& body,
                     const std::map<std::string, std::string>& headers,
                     std::string& response) override;
};

