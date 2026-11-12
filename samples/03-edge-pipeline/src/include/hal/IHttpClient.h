#pragma once
#include <string>
#include <map>

/**
 * =============================================================================
 * IHttpClient.h — Interfaz abstracta de cliente HTTP.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Abstracción para realizar POST HTTP con cabeceras personalizadas.
 *   Permite sustituir libcurl por un stub en pruebas unitarias o entornos
 *   sin red.
 *
 * IMPLEMENTACIONES:
 *   - DevStubHttpClient : responds {"status":"ok","stub":true} without leaving.
 *   - CloudManager::curlPost (does not implement IHttpClient).
 */
class IHttpClient {
public:
    virtual ~IHttpClient() = default;
    virtual bool postRequest(const std::string& url,
                             const std::string& body,
                             const std::map<std::string, std::string>& headers,
                             std::string& response) = 0;
};

