<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Cross-Origin Resource Sharing (CORS) Configuration
    |--------------------------------------------------------------------------
    |
    | Aquí defines qué orígenes pueden consumir la API. La autenticación usa
    | tokens Bearer de Sanctum (no cookies), por lo que supports_credentials
    | queda en false.
    |
    | NOTA (Fase 9 / despliegue): al publicar el frontend en Vercel, agregar el
    | dominio real de producción a allowed_origins. Si no, funciona en local
    | pero falla por CORS en producción.
    |
    */

    'paths' => ['api/*'],

    'allowed_methods' => ['*'],

    'allowed_origins' => [
        'http://localhost:5173', // Vite dev (frontend-react)
    ],

    'allowed_origins_patterns' => [],

    'allowed_headers' => ['*'],

    'exposed_headers' => [],

    'max_age' => 0,

    'supports_credentials' => false,

];
