/**
 * =============================================================================
 * cloud_manager.cpp — Implementación del gestor de sincronización con la nube.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Implementa CloudManager: lee la URL de la API desde env/config, cifra el
 *   payload con AES-256-GCM y lo envía vía libcurl o un IHttpClient
 *   inyectado. También implementa los comandos de nube: registerStudent,
 *   registerStaff, deleteStudent, wipeInstitution, verifyInstitution,
 *   verifyGroup.
 *
 * SECCIONES:
 *   1. loadApiUrl()          — resolución de NEXO_API_URL / config.json
 *   2. curlPost()            — POST real vía libcurl (SSL, timeouts)
 *   3. httpClientPost()      — POST vía IHttpClient (dev/tests)
 *   4. buildAuthenticatedRequest() — empaqueta JSON cifrado + inst_id + token
 *   5. syncRecord()          — envía el registro de asistencia
 *   6. Comandos de administración en la nube.
 */

#include "base_de_datos/cloud_manager.h"
#include "utils/Logger.h"
#include "utils/ConfigManager.h"
#include <curl/curl.h>
#include <string>
#include <nlohmann/json.hpp>
#include <fstream>
#include <cstdlib>
#include <chrono>

CloudManager::CloudManager() : m_apiUrl(loadApiUrl()) {}

std::string CloudManager::loadApiUrl() {
    const char* envUrl = std::getenv("NEXO_API_URL");
    if (envUrl && std::strlen(envUrl) > 0) return envUrl;
    // Preferir ConfigManager (ya cargado desde config.json del cwd)
    std::string cfgUrl = ConfigManager::getInstance().getString("api_url", "");
    if (!cfgUrl.empty()) return cfgUrl;
    // Fallback: /opt/nexo/config.json para despliegues en producción
    std::ifstream f("/opt/nexo/config.json");
    if (f.good()) {
        try {
            nlohmann::json j;
            f >> j;
            if (j.contains("api_url") && j["api_url"].is_string()) return j["api_url"];
        } catch (...) { LOG_WARN("Falló el parseo de /opt/nexo/config.json"); }
    }
    LOG_ERROR("NEXO_API_URL no está configurado y falta config.json. El edge no puede sincronizar.");
    return "";
}

// Construir la URL de ingesta: api_url base + "/ingest"
// El backend detecta los payloads del edge por la clave 'payload' en cualquier
// ruta, pero la raíz "/" devuelve 405 desde nginx. "/ingest" llega al handler PHP.
std::string CloudManager::getIngestUrl() const {
    std::string base = m_apiUrl;
    if (base.empty()) return "";
    // Quitar la barra final
    while (!base.empty() && base.back() == '/') base.pop_back();
    // Si ya termina en /ingest, no duplicar
    if (base.size() >= 7 && base.substr(base.size() - 7) == "/ingest") return base;
    return base + "/ingest";
}

static size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), size * nmemb);
    return size * nmemb;
}

static bool curlPost(const std::string& url, const std::string& postData,
                     const std::string& authToken, std::string& response) {
    CURL* curl = curl_easy_init();
    if (!curl) { LOG_ERROR("curl_easy_init falló"); return false; }

    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, "User-Agent: NEXO-Edge-RPi4/2.0");
    headers = curl_slist_append(headers, "Accept: application/json");
    if (!authToken.empty())
        headers = curl_slist_append(headers, ("X-NEXO-TOKEN: " + authToken).c_str());

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, postData.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 15L);

    CURLcode res = curl_easy_perform(curl);
    long httpCode = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        LOG_ERROR("curl falló: {}", curl_easy_strerror(res));
        return false;
    }
    // Aceptar 200 OK y 202 Accepted (el backend devuelve 202 para la ingesta del edge)
    if (httpCode != 200 && httpCode != 202) {
        LOG_ERROR("Sincronización con la nube HTTP {}: {}", httpCode, response.substr(0, 200));
        return false;
    }
    return true;
}

static bool httpClientPost(IHttpClient* client, const std::string& url,
                          const std::string& postData, const std::string& authToken,
                          std::string& response) {
    if (!client) return false;

    std::map<std::string, std::string> headers;
    headers["Content-Type"] = "application/json";
    headers["User-Agent"] = "NEXO-Edge-RPi4/2.0";
    headers["Accept"] = "application/json";
    if (!authToken.empty()) {
        headers["X-NEXO-TOKEN"] = authToken;
    }

    return client->postRequest(url, postData, headers, response);
}

// Serialización JSON segura usando nlohmann
static std::string jsonObj(std::initializer_list<std::pair<std::string, std::string>> kvs) {
    nlohmann::json j;
    for (auto& [k, v] : kvs) {
        j[k] = v;
    }
    return j.dump();
}

std::string CloudManager::buildAuthenticatedRequest(const std::string& jsonData, const std::string& instId) {
    Encryption& crypto = Encryption::getInstance();
    if (!crypto.isKeyProvisioned()) { LOG_ERROR("Clave AES no aprovisionada"); return ""; }
    std::string encrypted = crypto.encrypt(jsonData);
    if (encrypted.empty()) { LOG_ERROR("Falló el cifrado"); return ""; }

    nlohmann::json body;
    body["inst_id"] = instId;
    body["payload"] = encrypted;
    
    std::string token = crypto.getToken();
    if (crypto.isTokenProvisioned()) {
        body["token"] = token;
    }
    
    return body.dump();
}

bool CloudManager::syncRecord(const std::string& jsonData) {
    std::string body = buildAuthenticatedRequest(jsonData, m_instId);
    if (body.empty()) return false;
    std::string response;
    bool ok;

    // Usar el stub IHttpClient si está disponible (modo dev), si no libcurl real
    if (m_httpClient) {
        ok = httpClientPost(m_httpClient, getIngestUrl(), body, Encryption::getInstance().getToken(), response);
    } else {
        ok = curlPost(getIngestUrl(), body, Encryption::getInstance().getToken(), response);
    }

    if (ok) { LOG_DEBUG("Sincronización con la nube OK"); } else { LOG_ERROR("Falló la sincronización con la nube"); }
    return ok;
}

