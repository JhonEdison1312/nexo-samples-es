#pragma once
#include <cstdint>
#include <string>
#include <vector>

/**
 * =============================================================================
 * encryption.h — Interfaz singleton de criptografía del edge.
 * =============================================================================
 * RESPONSABILIDAD:
 *   Proporciona operaciones AES-256-GCM y gestión de la clave API/token en
 *   un singleton. Al inicializarse recupera la clave AES desde un archivo
 *   protegido (no la base de datos local) y el token API desde SQLite; al
 *   aprovisionarlos los persiste en esos mismos lugares. La clave se
 *   mantiene en memoria con mlock() cuando es posible y se limpia con
 *   OPENSSL_cleanse.
 *
 * FLUJO DE CIFRADO:
 *   texto plano + IV(12 aleatorio)
 *        │
 *        ▼
 *   AES-256-GCM -> ciphertext + etiqueta(16)
 *        │
 *        ▼
 *   packed = IV + ciphertext + etiqueta -> base64Encode
 *
 * DEPENDENCIAS:
 *   - OpenSSL (EVP_aes_256_gcm, RAND_bytes, BIO base64, mlock/munlock).
 *   - base_de_datos/sqlite_manager.h (para initialize()).
 */
class Encryption {
public:
    static Encryption& getInstance() {
        static Encryption instance;
        return instance;
    }

    bool initialize();
    void setKeyFile(const std::string& path);

    // Aprovisionamiento de clave
    bool isKeyProvisioned() const;
    bool isTokenProvisioned() const;
    bool provisionKey(const std::string& key);
    bool provisionToken(const std::string& token);

    // AES-256-GCM
    std::string encrypt(const std::string& plaintext);
    std::string encrypt(const std::string& plaintext, const std::vector<uint8_t>& iv);
    std::string decrypt(const std::string& ciphertext);

    // Hash con clave (HMAC-SHA256 en hex, determinista) para campos usados
    // como claves de búsqueda (p. ej. documento). Devuelve "" cuando no hay
    // clave aprovisionada — el llamador decide la degradación.
    std::string keyedHash(const std::string& plaintext);

    // Token
    std::string getToken() const;

private:
    Encryption() = default;
    ~Encryption();
    std::vector<char> m_aesKey;
    std::string m_apiToken;
    std::string m_keyFile = "nexo_edge.key";

    bool saveKeyToFile(const std::string& key);
    bool loadKeyFromFile(std::string& key);

    // Hardware binding — cifra la clave AES en disco con una clave derivada del serial del CPU
    std::string getHardwareBoundKey();  // Deriva clave de /proc/cpuinfo (Serial + Revision)
    bool saveKeyToFileEncrypted(const std::string& key);
    bool loadKeyFromFileEncrypted(std::string& key);
};

