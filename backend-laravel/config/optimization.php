<?php

/*
 * Configuracion del Motor de Optimizacion (Fase 4)
 * Ver el documento de arquitectura para la justificacion completa
 * Nada aqui es un valor fijo, puede ajustarse
 */

return [
    //Pesos de la formula del Score: Score = α·CostoCompra + β·PenalizacionDistancia
    // + γ·CostoTiempo − δ·BeneficioPromociones. Coeficientes independientes, no
    // pesos relativos (no necesitan sumar 1). Neutrales por defecto.
    // β pesa PenalizacionDistancia (normalizada 0–1), no un costo en $: su efecto
    // real es de criterio de desempate y queda por debajo de α. Ver ADR-05.
    'pesos' => [
        'alpha' => (float) env('OPTIMIZATION_ALPHA', 1.0), //peso del costo de la compra
        'beta' => (float) env('OPTIMIZATION_BETA',1.0), //peso de PenalizacionDistancia (desempate, no monetario)
        'gamma' => (float) env('OPTIMIZATION_GAMMA', 1.0), //peso del costo de tiempo
        'delta' => (float) env('OPTIMIZATION_DELTA', 1.0) //peso del beneficio de las promociones
    ],

    // Costo de combustible: RESERVADO para v2 (Google Maps Routes API + precios DGEHM).
    // Para el MVP se reemplazó por PenalizacionDistancia (normalizada sobre el set),
    // ver ADR-05 — no se dolariza combustible por imprecisión de Haversine + consumo.
    // 'combustible' => [
    //     'precio_por_litro' => (float) env('FUEL_PRICE', 4.25),
    //     'km_por_litro' => (float) env('VEHICLE_KM_PER_LITRE', 12),
    // ],

    // Costo de tiempo: supuesto del MVP, no modela tráfico real.
    // Costo de tiempo: supuesto del MVP, no modela tráfico real.
    'tiempo' => [
        'velocidad_promedio_kmh' => (float) env('VELOCIDAD_PROMEDIO_KMH', 30),
        'costo_por_minuto' => (float) env('COSTO_POR_MINUTO', 0.05),
    ],
];
