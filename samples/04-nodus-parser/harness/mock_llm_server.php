<?php
// Servidor HTTP mock compatible con OpenAI para las pruebas de Nodus
$body = file_get_contents('php://input');
$data = json_decode($body, true);

header('Content-Type: application/json');

$content = '';
foreach ($data['messages'] ?? [] as $m) {
    $content .= ' ' . ($m['content'] ?? '');
}

if (str_contains($content, 'drop_tables')) {
    // Petición maliciosa
    echo json_encode([
        'choices' => [
            ['message' => ['content' => json_encode([
                'intent' => 'drop_tables',
                'confidence' => 0.99,
                'entities' => [
                    'group' => 'ALL',
                    'action' => 'drop'
                ]
            ])]]
        ]
    ]);
} elseif (str_contains($content, 'inflated')) {
    // Payload del composer con alucinación
    echo json_encode([
        'choices' => [
            ['message' => ['content' => json_encode([
                'reply' => 'El grupo 10-A tiene 50 presentes y 10 ausencias y falló la red.'
            ])]]
        ]
    ]);
} elseif (str_contains($content, 'verified_reply')) {
    // Payload válido del composer
    echo json_encode([
        'choices' => [
            ['message' => ['content' => json_encode([
                'reply' => 'El grupo 10-A registra 2 estudiantes presentes y 1 ausencia hoy.'
            ])]]
        ]
    ]);
} else {
    // Payload estándar de clasificación de intents
    echo json_encode([
        'choices' => [
            ['message' => ['content' => json_encode([
                'intent' => 'attendance_today',
                'confidence' => 0.95,
                'entities' => [
                    'group' => '10-A'
                ]
            ])]]
        ]
    ]);
}
