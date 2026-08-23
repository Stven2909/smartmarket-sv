<?php

namespace App\Services\Optimization;

use App\Models\ListaCompra;
use App\Models\ResultadoOptimizacion;
use App\Services\ExpertSystemService;

class OptimizationService
{
    public function __construct(
        private ComparisonService $comparisonService,
        private DistanceService $distanceService,
        private ExpertSystemService $expertSystemService,
    ) {}

    // Tiempo estimado de desplazamiento, en minutos. Supuesto del MVP (velocidad
    // urbana promedio constante) — ver 02-arquitectura.md sección 5.1.
    public function calcularTiempoMinutos(float $distanciaKm): float
    {
        $velocidad = config('optimization.tiempo.velocidad_promedio_kmh');

        return round(($distanciaKm / $velocidad) * 60, 1);
    }

    // Costo en dólares asociado al tiempo de desplazamiento.
    public function calcularCostoTiempo(float $distanciaKm): float
    {
        $costoPorMinuto = config('optimization.tiempo.costo_por_minuto');

        return round($this->calcularTiempoMinutos($distanciaKm) * $costoPorMinuto, 2);
    }

    // La fórmula del Score, tal cual está congelada en 02-arquitectura.md sección 5.1
    // y actualizada por ADR-05: CostoCombustible ($) se reemplazó por
    // PenalizacionDistancia (normalizada 0–1). Mientras MENOR sea el Score, mejor
    // es la alternativa — es costo ajustado, no una calificación.
    public function calcularScore(float $costoCompra, float $penalizacionDistancia, float $costoTiempo, float $beneficioPromociones): float
    {
        $pesos = config('optimization.pesos');

        return round(
            $pesos['alpha'] * $costoCompra
            + $pesos['beta'] * $penalizacionDistancia
            + $pesos['gamma'] * $costoTiempo
            - $pesos['delta'] * $beneficioPromociones,
            4
        );
    }

    /**
     * Determina si una alternativa debe ser excluida del envío al Sistema Experto.
     * Retorna false si la alternativa es válida, o un string con el motivo de omisión.
     */
    public function debeOmitir(array $resultado, ?float $presupuesto, ?float $costoReferencia, ?float $distanciaMinima): string|false
    {
        if ($presupuesto === null) {
            return 'presupuesto_null';
        }

        if ($resultado['distancia_km'] === null) {
            return 'distancia_null';
        }

        if ($resultado['tiempo_minutos'] === null) {
            return 'tiempo_null';
        }

        if ($resultado['costo_total'] === null) {
            return 'costo_total_null';
        }

        if ($resultado['productos_totales'] <= 0) {
            return 'productos_totales_cero';
        }

        if ($resultado['productos_disponibles'] < 0) {
            return 'productos_disponibles_negativo';
        }

        if ($resultado['productos_disponibles'] > $resultado['productos_totales']) {
            return 'productos_disponibles_mayor_que_totales';
        }

        if ($resultado['productos_esenciales_disponibles'] < 0) {
            return 'esenciales_disponibles_negativo';
        }

        if ($resultado['productos_esenciales_disponibles'] > $resultado['productos_esenciales_totales']) {
            return 'esenciales_disponibles_mayor_que_totales';
        }

        if ($resultado['productos_esenciales_totales'] < 0) {
            return 'esenciales_totales_negativo';
        }

        if ($costoReferencia === null) {
            return 'costo_referencia_indeterminado';
        }

        if ($distanciaMinima === null) {
            return 'distancia_minima_indeterminada';
        }

        return false;
    }

    /**
     * Construye el payload para el endpoint POST /api/v1/recommend del Sistema Experto.
     */
    public function construirPayload(array $resultado, ListaCompra $lista, float $costoReferencia, float $distanciaMinima, int $numeroSupermercados): array
    {
        $ahorro = max(0.0, round($costoReferencia - (float) $resultado['costo_total'], 2));
        $distanciaAdicional = max(0.0, round((float) $resultado['distancia_km'] - $distanciaMinima, 2));

        return [
            'request_id' => 'lista-' . $lista->id . '-sucursal-' . $resultado['sucursal_id'],
            'alternativa_id' => 'sucursal-' . $resultado['sucursal_id'],
            'costo_total' => round((float) $resultado['costo_total'], 2),
            'presupuesto' => (float) $lista->presupuesto,
            'ahorro' => $ahorro,
            'distancia_km' => round((float) $resultado['distancia_km'], 2),
            'distancia_adicional_km' => $distanciaAdicional,
            'tiempo_estimado_min' => round((float) $resultado['tiempo_minutos'], 1),
            'productos_disponibles' => $resultado['productos_disponibles'],
            'productos_totales' => $resultado['productos_totales'],
            'productos_esenciales_disponibles' => $resultado['productos_esenciales_disponibles'],
            'productos_esenciales_totales' => $resultado['productos_esenciales_totales'],
            'numero_supermercados' => $numeroSupermercados,
            'promociones_aplicables' => (float) ($resultado['beneficio_promociones'] ?? 0) > 0,
        ];
    }

    /**
     * Calcula productos_disponibles para una alternativa (esenciales + opcionales).
     */
    private function calcularProductosDisponibles(array $resultado): int
    {
        return $resultado['productos_esenciales_disponibles'] + $resultado['productos_opcionales_disponibles'];
    }

    /**
     * Calcula productos_totales para una alternativa (esenciales + opcionales).
     */
    private function calcularProductosTotales(array $resultado): int
    {
        return $resultado['productos_esenciales_totales'] + $resultado['productos_opcionales_totales'];
    }

    // Orquesta todo el flujo: ComparisonService → DistanceService → Score →
    // persistencia en ResultadoOptimizacion. Este es el método que consume el
    // controlador; el controlador no calcula nada, solo coordina la petición.
    public function optimizar(ListaCompra $lista, float $latUsuario, float $lngUsuario): array
    {
        $comparacion = $this->comparisonService->comparar($lista);

        foreach ($comparacion['resultados'] as &$resultado) {
            // ADR-11: alternativas sin coordenadas (Sucursal "Tienda en línea") no
            // compiten en el eje físico — no tienen distancia ni tiempo de viaje.
            // Siguen siendo válidas por su costo de compra a nivel nacional.
            if ($resultado['latitud'] === null || $resultado['longitud'] === null) {
                $resultado['distancia_km'] = null;
                $resultado['tiempo_minutos'] = null;
                $resultado['costo_tiempo'] = null;

                continue;
            }

            $distancia = $this->distanceService->calcularHaversine(
                $latUsuario,
                $lngUsuario,
                $resultado['latitud'],
                $resultado['longitud'],
            );

            // Pase 1: señales que dependen solo de esta alternativa.
            $resultado['distancia_km'] = $distancia;
            $resultado['tiempo_minutos'] = $this->calcularTiempoMinutos($distancia);
            $resultado['costo_tiempo'] = $this->calcularCostoTiempo($distancia);
        }
        unset($resultado);

        // Normalización de la distancia contra el set (PenalizacionDistancia 0–1):
        // 0 = sucursal más cercana, 1 = la más lejana. Si todas miden lo mismo
        // (o hay una sola alternativa) la penalización es 0. No se dolariza la
        // distancia — sigue ADR-05. Las alternativas sin coordenadas (ADR-11)
        // quedan fuera del min/max. Ver 02-arquitectura.md §5.1.
        $distancias = array_values(array_filter(
            array_column($comparacion['resultados'], 'distancia_km'),
            fn ($d) => $d !== null,
        ));
        $distanciaMin = $distancias === [] ? 0.0 : min($distancias);
        $distanciaMax = $distancias === [] ? 0.0 : max($distancias);
        $distanciaRango = $distanciaMax - $distanciaMin;

        foreach ($comparacion['resultados'] as &$resultado) {
            // Pase 2: penalización normalizada + Score. La tienda online no
            // recorre distancia física ⇒ penalización 0 (ADR-11).
            $penalizacionDistancia = $resultado['distancia_km'] === null
                ? 0.0
                : ($distanciaRango > 0
                    ? round(($resultado['distancia_km'] - $distanciaMin) / $distanciaRango, 4)
                    : 0.0);

            $resultado['penalizacion_distancia'] = $penalizacionDistancia;
            $resultado['score'] = $this->calcularScore(
                $resultado['costo_total'],
                $penalizacionDistancia,
                $resultado['costo_tiempo'],
                $resultado['beneficio_promociones'],
            );
        }
        unset($resultado);

        // Menor Score = mejor alternativa.
        usort($comparacion['resultados'], fn ($a, $b) => $a['score'] <=> $b['score']);
        $comparacion['resultados'] = array_values($comparacion['resultados']);

        // "Nivel de optimización" (0-100): posición relativa de cada alternativa dentro
        // del conjunto evaluado, derivada de los Scores reales de la fórmula congelada
        // (02-arquitectura.md §5.1). No es una predicción ni personalización: mide qué
        // tan destacada quedó una opción frente a las demás en esta optimización.
        // Si todas empatan (scorePeor === scoreMejor, ej. una sola sucursal), vale 100.
        $mejorScore = $comparacion['resultados'][0]['score'] ?? null;
        $peorScore = end($comparacion['resultados'])['score'] ?? null;

        foreach ($comparacion['resultados'] as &$resultado) {
            $resultado['nivel_optimizacion'] = ($peorScore !== null && $peorScore > $mejorScore)
                ? round(100 * ($peorScore - $resultado['score']) / ($peorScore - $mejorScore))
                : 100;
        }
        unset($resultado);

        // Enriquecer con productos_disponibles y productos_totales (requeridos
        // por el contrato del Sistema Experto).
        foreach ($comparacion['resultados'] as &$resultado) {
            $resultado['productos_disponibles'] = $this->calcularProductosDisponibles($resultado);
            $resultado['productos_totales'] = $this->calcularProductosTotales($resultado);
        }
        unset($resultado);

        // --- Sistema Experto: calcular referencias, validar y enviar payloads ---
        $costoReferencia = $this->calcularCostoReferencia($comparacion['resultados']);
        $distanciaMinima = $this->calcularDistanciaMinima($comparacion['resultados']);
        $numeroSupermercados = $this->contarSupermercadosUnicos($comparacion['resultados']);

        $payloadsValidos = [];

        foreach ($comparacion['resultados'] as &$resultado) {
            $motivo = $this->debeOmitir($resultado, $lista->presupuesto, $costoReferencia, $distanciaMinima);

            if ($motivo !== false) {
                $resultado['recommendation'] = null;
                $resultado['expert_system_available'] = false;
                $resultado['expert_omission_reason'] = $motivo;
            } else {
                $resultado['recommendation'] = null;
                $resultado['expert_system_available'] = false;
                $resultado['expert_omission_reason'] = null;
                $payloadsValidos[] = $this->construirPayload($resultado, $lista, $costoReferencia, $distanciaMinima, $numeroSupermercados);
            }
        }
        unset($resultado);

        // Llamar al Sistema Experto una sola vez con todos los payloads válidos.
        if ($payloadsValidos !== []) {
            $respuestas = $this->expertSystemService->recommend($payloadsValidos);

            if ($respuestas !== null) {
                foreach ($comparacion['resultados'] as &$resultado) {
                    $requestId = 'lista-' . $lista->id . '-sucursal-' . $resultado['sucursal_id'];
                    if (isset($respuestas[$requestId]) && is_array($respuestas[$requestId])) {
                        $resultado['recommendation'] = $respuestas[$requestId];
                        $resultado['expert_system_available'] = true;
                    }
                }
                unset($resultado);
            }
        }

        $mejorOpcion = $comparacion['resultados'][0] ?? null;
        $peorOpcion = end($comparacion['resultados']) ?: null;

        $resultadoGuardado = null;

        if ($mejorOpcion) {
            $ahorro = $peorOpcion ? round($peorOpcion['costo_total'] - $mejorOpcion['costo_total'], 2) : 0;

            $resultadoGuardado = ResultadoOptimizacion::create([
                'lista_compra_id' => $lista->id,
                'score' => $mejorOpcion['score'],
                'ahorro' => $ahorro,
                // Nullable desde ADR-11: la mejor opción puede ser una Tienda
                // en línea sin distancia/tiempo aplicables.
                'distancia' => $mejorOpcion['distancia_km'],
                'tiempo' => $mejorOpcion['tiempo_minutos'] === null ? null : (int) round($mejorOpcion['tiempo_minutos']),
                'supermercados' => array_map(
                    fn ($r) => ['supermercado' => $r['supermercado'], 'sucursal' => $r['sucursal'], 'score' => $r['score']],
                    $comparacion['resultados']
                ),
                'resultado_json' => $comparacion,
                'fecha' => now(),
            ]);
        }

        return [
            'lista' => $comparacion['lista'],
            'presupuesto' => $comparacion['presupuesto'],
            'mejor_opcion' => $mejorOpcion,
            'resultados' => $comparacion['resultados'],
            'resultado_optimizacion_id' => $resultadoGuardado?->id,
        ];
    }

    /**
     * Calcula costo_referencia = max(costo_total) entre alternativas válidas
     * (con costo_total no nulo).
     */
    private function calcularCostoReferencia(array $resultados): ?float
    {
        $costos = array_filter(
            array_column($resultados, 'costo_total'),
            fn ($c) => $c !== null,
        );

        return $costos === [] ? null : (float) max($costos);
    }

    /**
     * Calcula distancia_minima = min(distancia_km) entre alternativas con coordenadas.
     */
    private function calcularDistanciaMinima(array $resultados): ?float
    {
        $distancias = array_values(array_filter(
            array_column($resultados, 'distancia_km'),
            fn ($d) => $d !== null,
        ));

        return $distancias === [] ? null : (float) min($distancias);
    }

    /**
     * Cuenta supermercados únicos entre las alternativas.
     */
    private function contarSupermercadosUnicos(array $resultados): int
    {
        $ids = array_unique(array_column($resultados, 'supermercado_id'));

        return count($ids);
    }
}
