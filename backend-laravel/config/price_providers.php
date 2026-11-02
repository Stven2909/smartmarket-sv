<?php

// Registro de fuentes de precios (Price Providers intercambiables).
// Principio rector (02-arquitectura.md §6.1 / ADR-006): ninguna fuente es
// irremplazable — cada una tiene interruptor propio y apagarla no afecta al resto.
//
// Veredicto legal por fuente: docs/06-referencia-extractor-vtex.md §5.
// Alcance y condiciones operativas obligatorias: docs/07-decision-extractor-fuentes-riesgo.md (ADR-10).
// Actualización 2026-11-01 (ADR-012): solo Super Selectos se sincroniza por webscraping.
// Walmart, Maxi Despensa, Don Juan y PriceSmart quedan como datos mock de seeder.
return [

    'sincronizacion' => [
        // Lista blanca operativa: el comando precios:sync y precios:procesar solo
        // aceptan estas fuentes. El resto se considera mock/carga manual.
        'fuentes_permitidas' => ['super-selectos'],
        'fuente_por_defecto' => 'super-selectos',
    ],

    'defaults' => [
        // Obligación del ADR-10: User-Agent identificable, nunca suplantar navegador.
        // PENDIENTE antes de la primera corrida real: definir PRICE_REPO_URL y
        // PRICE_CONTACTO en .env con valores verdaderos.
        'user_agent' => sprintf(
            '%s/%s (+%s; %s)',
            env('PRICE_BOT_NAME', 'SmartMarketSV-AcademicBot'),
            env('PRICE_BOT_VERSION', '1.0'),
            env('PRICE_REPO_URL', 'URL-DEL-REPO-PENDIENTE'),
            env('PRICE_CONTACTO', 'correo-institucional-pendiente'),
        ),

        // Cortesía estricta: pausa entre requests, reintentos solo ante 429/503,
        // agotados ⇒ abortar la corrida completa. Jamás evadir bloqueos/captchas.
        'pausa_ms' => (int) env('PRICE_PAUSA_MS', 1500),
        'reintentos' => 3,
        'backoff_ms' => 500,
        'timeout_segundos' => 30,
    ],

    'fuentes' => [

        'super-selectos' => [
            'modo' => 'html',
            'base_url' => 'https://www.superselectos.com/',
            // Páginas de listado a recorrer; paginación profunda queda para después.
            'urls_listado' => ['https://www.superselectos.com/'],
            // Supermercado dueño de los precios (StagingProcessor crea/reutiliza
            // su sucursal virtual "Tienda en línea", ADR-11).
            'supermercado' => 'Super Selectos',
            'enabled' => true,
            'mock' => false,
            'notas' => 'Única cadena que se sincroniza por webscraping (ADR-012); ToS sin cláusulas anti-extracción (doc 06 §5.1).',
        ],

        'walmart' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.walmart.com.sv',
            'supermercado' => 'Walmart',
            'enabled' => false,
            'mock' => true,
            'notas' => 'Sincronización deshabilitada (ADR-012); sus precios vienen de MockSupermarketsSeeder.',
        ],

        'maxi-despensa' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.maxidespensa.com.sv',
            'supermercado' => 'Maxi Despensa',
            'enabled' => false,
            'mock' => true,
            'notas' => 'Sincronización deshabilitada (ADR-012); sus precios vienen de MockSupermarketsSeeder.',
        ],

        'don-juan' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.ladespensadedonjuan.com.sv',
            'supermercado' => 'La Despensa de Don Juan',
            'enabled' => false,
            'mock' => true,
            'notas' => 'Sincronización deshabilitada (ADR-012); sus precios vienen de MockSupermarketsSeeder.',
        ],

        // Excluido de la automatización por decisión expresa del ADR-10: su
        // robots.txt prohíbe scrapers por nombre. Permanece como fuente manual
        // y ahora también recibe datos mock (ADR-012).
        'pricesmart' => [
            'modo' => 'manual',
            'supermercado' => 'PriceSmart',
            'enabled' => false,
            'mock' => true,
            'notas' => 'robots.txt bloquea scrapers nominalmente (doc 06 §5.3) — datos mock de seeder.',
        ],

        // Reservado v1.2: requiere convenio comercial + token (fuente partner-feed).
        'san-francisco' => [
            'modo' => 'partner-feed',
            'supermercado' => 'Súper San Francisco',
            'enabled' => false,
            'mock' => false,
            'notas' => 'Requiere acuerdo comercial (doc 06 §1).',
        ],
    ],
];
