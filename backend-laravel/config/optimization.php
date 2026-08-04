<?php

/*
 * Configuracion del Motor de Optimizacion (Fase 4)
 * Ver el documento de arquitectura para la justificacion completa
 * Nada aqui es un valor fijo, puede ajustarse
 */

return [
    //Pesos de la formula del Score: Score = α·CostoCompra + β·CostoCombustible
    // + γ·CostoTiempo − δ·BeneficioPromociones. Coeficientes independientes, no
    //pesos relativos (no necesitan sumar 1). Neutrales por defecto.
    'pesos' => [
        'alpha' => (float) env('OPTIMIZATION_ALPHA', 1.0), //peso del costo de la compra
        'beta' => (float) env('OPTIMIZATION_BETA',1.0), //peso del costo de combustible
        'gamma' => (float) env('OPTIMIZATION_GAMMA', 1.0), //peso del costo de tiempo
        'delta' => (float) env('OPTIMIZATION_DELTA', 1.0) //peso del beneficio de las promociones
    ],

    //Costo de combustible, se calcula asi = (distancia_km / km_por_litro) * precio_por_litro
    'combustible' => [
        'precio_por_litro' => (float) env('FUEL_PRICE', 4.25),
        'km_por_litro' => (float) env('VEHICLE_KM_PER_LITRE', 12),
    ],

    // Costo de tiempo: supuesto del MVP, no modela tráfico real.
    'tiempo' => [
        'velocidad_promedio_kmh' => (float) env('VELOCIDAD_PROMEDIO_KMH', 30),
        'costo_por_minuto' => (float) env('COSTO_POR_MINUTO', 0.05),
    ],
];
