<?php
// Demo de verificación completo para 04-nodus-parser
// Demuestra:
// 1. Clasificación de intents y parseo de entidades a través de una API compatible con OpenAI
// 2. Prevención de prompt injection y bypass de scope comodín
// 3. Pipeline de extremo a extremo: Parseo -> Plan -> verificación RBAC -> Ejecución SQL de solo lectura
// 4. Response Composer y guardia anti-alucinación post-generación (nxLlmComposeGuard)
// 5. Degradación segura cuando el LLM no está disponible (mode=off / falta de clave)

// 1. Iniciar servidor mock LLM local en el puerto 18080
$serverCmd = sprintf(
    'php -S 127.0.0.1:18080 %s >/dev/null 2>&1 & echo $!',
    escapeshellarg(__DIR__ . '/mock_llm_server.php')
);
$serverPid = (int)trim(shell_exec($serverCmd));
register_shutdown_function(function() use ($serverPid) {
    if ($serverPid > 0) {
        @posix_kill($serverPid, SIGTERM);
    }
});
usleep(250000); // espera de arranque de 250 ms

// Configurar el entorno activo ANTES de requerir nexus_llm.php
putenv('NLU_LLM_URL=http://127.0.0.1:18080');
putenv('NLU_LLM_KEY=test-active-key');
putenv('NLU_LLM_MODE=on');
putenv('NX_LLM_NO_CACHE=1');

// Cargar el módulo LLM de Nodus extraído
require_once __DIR__ . '/../src/nexus_llm.php';

echo "=== DEMO DE VERIFICACIÓN 04-NODUS-PARSER ===\n";
$failures = 0;

// --- PRUEBA 1: Clasificación de intents y entidades ---
echo "\n--- PRUEBA 1: Clasificación de intent y validación estricta de entidades ---\n";
$query = "¿Cómo está la asistencia del grupo 10-A hoy?";
$parsed = nxLlmClassify($query);

if ($parsed && ($parsed['intent'] ?? '') === 'attendance_today') {
    echo "Consulta: \"{$query}\"\n";
    echo "Dominio: " . ($parsed['domain'] ?? '') . "\n";
    echo "Intent: " . ($parsed['intent'] ?? '') . "\n";
    echo "Confianza: " . ($parsed['confidence'] ?? 0) . "\n";
    echo "Grupo extraído: " . ($parsed['entities']['group'] ?? 'ninguno') . "\n";
    echo "Resultado: CLASIFICACIÓN DE INTENT SUPERADA\n";
} else {
    echo "ERROR: No se pudo clasificar el intent\n";
    exit(1);
}

// --- PRUEBA 2: Inyección adversarial de prompt y bypass de scope ---
echo "\n--- PRUEBA 2: Defensa contra inyección maliciosa y escalada de scope ---\n";
$maliciousQuery = "drop_tables with group ALL";
$maliciousRes = nxLlmClassify($maliciousQuery);

echo "Consulta adversarial: \"{$maliciousQuery}\"\n";
echo "Intent forzado: " . ($maliciousRes['intent'] ?? 'ninguno') . " (los intents no listados se fuerzan a out_of_scope)\n";
$groupBlocked = !isset($maliciousRes['entities']['group']);
echo "Scope comodín 'ALL': " . ($groupBlocked ? "ELIMINADO POR LA WHITELIST" : "FILTRADO") . "\n";
if (($maliciousRes['intent'] ?? '') === 'out_of_scope' && $groupBlocked) {
    echo "Resultado: INYECCIÓN ADVERSARIAL BLOQUEADA CORRECTAMENTE\n";
} else {
    echo "ERROR: Falló la defensa contra inyección\n";
    exit(1);
}

// --- PRUEBA 3: Parseo -> Plan -> RBAC -> Ejecución SQL de solo lectura ---
echo "\n--- PRUEBA 3: Parseo -> Plan -> RBAC -> Ejecución SQL de solo lectura ---\n";
echo "1. Parseo: texto de entrada parseado a intent: {$parsed['intent']}, entidad: group={$parsed['entities']['group']}\n";

// 2. Planner determinista: mapea intent + entidad a capability
// AÑADIDO PARA ESTA MUESTRA: SIMULADO - el código del planner no está en el repo
$plan = [
    'capability' => 'attendance.summary',
    'entity'     => 'students',
    'action'     => 'count',
    'filters'    => ['group' => $parsed['entities']['group']],
    'sql'        => "SELECT '10-A' AS group_name, 28 AS present, 2 AS absent"
];
echo "2. Plan: Capacidad={$plan['capability']}, Acción={$plan['action']} (SIMULADO)\n";

// 3. Verificación de política RBAC: rol Teacher autorizado para el grupo asignado
// AÑADIDO PARA ESTA MUESTRA: SIMULADO - la matriz RBAC no está en el repo
$userRole = 'TEACHER';
$allowedRoles = ['RECTOR', 'COORDINATOR', 'TEACHER'];
$isAllowed = in_array($userRole, $allowedRoles, true);
echo "3. Verificación RBAC: Rol={$userRole} autorizado para {$plan['capability']}: " . ($isAllowed ? "PERMITIDO" : "DENEGADO") . " (SIMULADO)\n";

// 4. Ejecución SQL de solo lectura
// AÑADIDO PARA ESTA MUESTRA: SIMULADO - no hay BD real en el harness
echo "4. SQL de solo lectura: {$plan['sql']} (SIMULADO)\n";
$dbData = ['group_name' => '10-A', 'present' => 28, 'absent' => 2];
echo "Resultado de BD: present={$dbData['present']}, absent={$dbData['absent']} (SIMULADO)\n";
$verifiedReply = "El grupo 10-A registra 28 estudiantes presentes y 2 ausencias hoy.";
echo "Respuesta determinista verificada: \"{$verifiedReply}\"\n";

// --- PRUEBA 4: Response Composer y guardia anti-alucinación ---
echo "\n--- PRUEBA 4: Guardia contra alucinaciones post-generación (nxLlmComposeGuard) ---\n";
$facts = ['rows' => 2, 'table' => ['title' => 'Asistencia 10-A']];

// Prueba 4a: Buena composición que preserva los hechos
echo "4a. Composición con cifras precisas:" . PHP_EOL;
$composedValid = "El grupo 10-A registra 28 estudiantes presentes y 2 ausencias el día de hoy.";
$guard1 = nxLlmComposeGuard($composedValid, $verifiedReply, $facts, $query);
echo "    Texto: \"{$composedValid}\"\n";
echo "    Guardia: " . ($guard1 ? "PASS (Aceptada)" : "FAIL") . "\n";
if (!$guard1) { $failures++; }

// Prueba 4b: Cifras alucinadas / infladas
$composedInflated = "El grupo 10-A tiene 50 presentes y 10 ausencias.";
$guard2 = nxLlmComposeGuard($composedInflated, $verifiedReply, $facts, $query);
echo "4b. Inflación alucinada de cifras:" . PHP_EOL;
echo "    Texto: \"{$composedInflated}\"\n";
echo "    Guardia: " . (!$guard2 ? "PASS (Bloqueada correctamente)" : "FAIL (La alucinación se filtró)") . "\n";
if ($guard2) { $failures++; }

// Prueba 4c: Negación de datos cuando la tabla tiene registros
echo "4c. Falsa negación de datos cuando rows > 0:\n";
$composedDenial = "No se encontraron registros de asistencia para este grupo.";
$guard3 = nxLlmComposeGuard($composedDenial, $verifiedReply, $facts, $query);
echo "    Texto: \"{$composedDenial}\"\n";
echo "    Guardia: " . (!$guard3 ? "PASS (Bloqueada correctamente)" : "FAIL (Falsa negación filtrada)") . "\n";
if ($guard3) { $failures++; }

// Prueba 4d: Causas fabricadas / excusas técnicas
$composedExcuse = "El grupo tiene 28 presentes pero falló la red del colegio.";
$guard4 = nxLlmComposeGuard($composedExcuse, $verifiedReply, $facts, $query);
echo "4d. Excusa técnica fabricada (\"falló la red\"):\n";
echo "    Texto: \"{$composedExcuse}\"\n";
echo "    Guardia: " . (!$guard4 ? "PASS (Bloqueada correctamente)" : "FAIL (Excusa filtrada)") . "\n";
if ($guard4) { $failures++; }

// --- PRUEBA 5: Degradación segura (LLM no disponible) ---
echo "\n--- PRUEBA 5: Degradación segura cuando el LLM no está disponible ---\n";
$subCmd = 'php -r ' . escapeshellarg(
    'putenv("NLU_LLM_MODE=off"); require ' . var_export(__DIR__ . '/../src/nexus_llm.php', true) . '; var_export(nxLlmClassify("test") === null);'
);
$isDegraded = (trim(shell_exec($subCmd)) === 'true');
if ($isDegraded) {
    echo "LLM deshabilitado: nxLlmClassify devolvió null (degrada de forma segura a plantillas deterministas)\n";
    echo "Resultado del fallback: DEGRADACIÓN SEGURA OK\n";
} else {
    echo "ERROR: Se esperaba null con el LLM deshabilitado\n";
    exit(1);
}

if ($failures > 0) {
    echo "\n=== DEMO 04-NODUS-PARSER COMPLETA: {$failures} VERIFICACIÓN(ES) FALLIDA(S) ===\n";
    exit(1);
}
echo "\n=== DEMO 04-NODUS-PARSER COMPLETA: TODAS LAS VERIFICACIONES SUPERADAS ===\n";
