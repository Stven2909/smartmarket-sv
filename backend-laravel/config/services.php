<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    'expert_system' => [
        'url' => env('EXPERT_SYSTEM_URL', 'https://sistema-experto-fork.onrender.com'),
        'api_key' => env('EXPERT_SYSTEM_API_KEY'),
        'timeout' => (int) env('EXPERT_SYSTEM_TIMEOUT', 15),
        'connect_timeout' => (float) env('EXPERT_SYSTEM_CONNECT_TIMEOUT', 5),
        'retry_times' => (int) env('EXPERT_SYSTEM_RETRY_TIMES', 3),
        'retry_sleep_ms' => (int) env('EXPERT_SYSTEM_RETRY_SLEEP_MS', 2000),
        // Presupuesto total para una corrida de optimización. Evita que un
        // Render frío, varios reintentos o muchas sucursales bloqueen la
        // petición del usuario más allá de lo razonable.
        'total_budget_ms' => (int) env('EXPERT_SYSTEM_TOTAL_BUDGET_MS', 25000),
    ],

];
