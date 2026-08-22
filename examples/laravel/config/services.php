<?php

declare(strict_types=1);

return [
    'expert_system' => [
        'url' => env('EXPERT_SYSTEM_URL', 'http://127.0.0.1:8001'),
        'timeout' => (int) env('EXPERT_SYSTEM_TIMEOUT', 3),
        'retry_times' => (int) env('EXPERT_SYSTEM_RETRY_TIMES', 1),
    ],
];
