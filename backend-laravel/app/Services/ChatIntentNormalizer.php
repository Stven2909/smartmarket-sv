<?php

namespace App\Services;

use Illuminate\Support\Str;

/**
 * Traduce las preguntas del chat a la formulación canónica que el Sistema
 * Experto clasifica de forma determinista.
 *
 * El clasificador del servicio Python es por palabras clave y es sensible a la
 * redacción: por ejemplo, "¿Qué tan lejos queda esta tienda?" cae en
 * PRESUPUESTO, mientras que "¿Cuál es la distancia?" se reconoce como DISTANCIA.
 * Además, la versión desplegada no tiene una intención propia para promociones.
 *
 * Esta clase detecta el tema real de la pregunta (sin tildes y sin depender de
 * una frase exacta) y devuelve:
 *  - `intent`: tema detectado, o null si no se reconoce.
 *  - `message`: pregunta canónica que el experto sí entiende.
 *
 * Si no se reconoce el tema, el mensaje original se envía sin cambios para que
 * el experto decida (por ejemplo, responder con AYUDA).
 */
class ChatIntentNormalizer
{
    /**
     * Preguntas canónicas verificadas contra el servicio desplegado.
     */
    private const MENSAJES = [
        'PROMOCIONES' => '¿Hay promociones aplicables?',
        'DISTANCIA' => '¿Cuál es la distancia?',
        'TIEMPO' => '¿Cuánto tiempo tardo en llegar?',
        'PRODUCTOS' => '¿Están todos los productos disponibles?',
        'PRESUPUESTO' => '¿La compra cabe en mi presupuesto?',
        'AHORRO' => '¿Cuánto me ahorro?',
        'EXPLICACION' => '¿Por qué me recomiendas esta alternativa?',
    ];

    /**
     * Palabras clave por tema. El orden también define el desempate: si dos
     * temas empatan en coincidencias, gana el que aparece primero.
     */
    private const CLAVES = [
        'PROMOCIONES' => [
            'promocion', 'promociones', 'promo', 'promos',
            'descuento', 'descuentos', 'oferta', 'ofertas',
            'rebaja', 'rebajas', 'cupon', 'cupones',
        ],
        'DISTANCIA' => [
            'distancia', 'lejos', 'lejano', 'lejana', 'cerca', 'cercano', 'cercana',
            'kilometro', 'kilometros', 'km', 'recorrido', 'recorrer',
        ],
        'TIEMPO' => [
            'tiempo', 'minuto', 'minutos', 'tarda', 'tardo', 'tardaria',
            'demora', 'demoro', 'viaje', 'traslado', 'rapido', 'rapida', 'llegar',
        ],
        'PRODUCTOS' => [
            'producto', 'productos', 'disponible', 'disponibles',
            'esencial', 'esenciales', 'completo', 'completa', 'consigo',
        ],
        'PRESUPUESTO' => [
            'presupuesto', 'cabe', 'alcanza', 'sobra', 'sobran',
            'falta', 'faltan', 'dinero', 'plata', 'cuesta', 'costar',
        ],
        'AHORRO' => [
            'ahorro', 'ahorros', 'ahorrar', 'ahorraria', 'barato', 'barata',
            'economico', 'economica', 'diferencia',
        ],
        'EXPLICACION' => [
            'recomiendas', 'recomienda', 'recomendacion',
            'explicame', 'explica', 'explicacion', 'conviene',
            'por que', 'porque',
        ],
    ];

    /**
     * @return array{intent: string|null, message: string, rewritten: bool}
     */
    public function normalizar(string $mensaje): array
    {
        $intent = $this->detectar($mensaje);

        if ($intent === null) {
            return [
                'intent' => null,
                'message' => $mensaje,
                'rewritten' => false,
            ];
        }

        $canonica = self::MENSAJES[$intent];

        return [
            'intent' => $intent,
            'message' => $canonica,
            'rewritten' => $canonica !== $mensaje,
        ];
    }

    /**
     * Devuelve el tema con más coincidencias. Empate: gana el orden de CLAVES.
     */
    private function detectar(string $mensaje): ?string
    {
        $texto = preg_replace('/\s+/', ' ', Str::lower(Str::ascii($mensaje))) ?? '';

        $mejorIntent = null;
        $mejorPuntaje = 0;

        foreach (self::CLAVES as $intent => $claves) {
            $puntaje = 0;

            foreach ($claves as $clave) {
                if (preg_match('/\b'.preg_quote($clave, '/').'\b/u', $texto) === 1) {
                    $puntaje++;
                }
            }

            if ($puntaje > $mejorPuntaje) {
                $mejorPuntaje = $puntaje;
                $mejorIntent = $intent;
            }
        }

        return $mejorIntent;
    }
}
