<?php

// Registro de fuentes de precios (Price Providers intercambiables).
// Principio rector (02-arquitectura.md §6.1 / ADR-006): ninguna fuente es
// irremplazable — cada una tiene interruptor propio y apagarla no afecta al resto.
//
// Veredicto legal por fuente: docs/06-referencia-extractor-vtex.md §5.
// Alcance y condiciones operativas obligatorias: docs/07-decision-extractor-fuentes-riesgo.md (ADR-10).
return [

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
            'enabled' => true,
            'notas' => 'Única cadena independiente; ToS sin cláusulas anti-extracción (doc 06 §5.1).',
        ],

        'walmart' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.walmart.com.sv',
            'enabled' => true,
            'notas' => 'Operadora del Sur; ToS restrictivo — automatiza bajo ADR-10.',
        ],

        'maxi-despensa' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.maxidespensa.com.sv',
            'enabled' => true,
            'notas' => 'Misma entidad que Walmart (inferencia fuerte, doc 06 §5.2).',
        ],

        'don-juan' => [
            'modo' => 'vtex',
            'base_url' => 'https://www.ladespensadedonjuan.com.sv',
            'enabled' => true,
            'notas' => 'ToS verificado idéntico al de walmart.com.sv.',
        ],

        // Excluido de la automatización por decisión expresa del ADR-10: su
        // robots.txt prohíbe scrapers por nombre. Permanece como fuente manual.
        'pricesmart' => [
            'modo' => 'manual',
            'enabled' => false,
            'notas' => 'robots.txt bloquea scrapers nominalmente (doc 06 §5.3) — carga manual.',
        ],

        // Reservado v1.2: requiere convenio comercial + token (fuente partner-feed).
        'san-francisco' => [
            'modo' => 'partner-feed',
            'enabled' => false,
            'notas' => 'Requiere acuerdo comercial (doc 06 §1).',
        ],
    ],
];
