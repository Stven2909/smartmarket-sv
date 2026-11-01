<?php

namespace Tests\Unit;

use App\Services\ChatIntentNormalizer;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class ChatIntentNormalizerTest extends TestCase
{
    private ChatIntentNormalizer $normalizer;

    protected function setUp(): void
    {
        parent::setUp();

        $this->normalizer = new ChatIntentNormalizer;
    }

    /**
     * Las 7 preguntas guía de la UI deben reconocerse y reescribirse a la
     * formulación canónica que el experto clasifica correctamente.
     */
    #[DataProvider('preguntasGuia')]
    public function test_reconoce_las_preguntas_guia(string $mensaje, string $intent, string $canonica): void
    {
        $resultado = $this->normalizer->normalizar($mensaje);

        $this->assertSame($intent, $resultado['intent']);
        $this->assertSame($canonica, $resultado['message']);
    }

    public static function preguntasGuia(): array
    {
        return [
            'explicación' => [
                '¿Por qué me recomiendas esta alternativa?',
                'EXPLICACION',
                '¿Por qué me recomiendas esta alternativa?',
            ],
            'ahorro' => ['¿Cuánto me ahorro?', 'AHORRO', '¿Cuánto me ahorro?'],
            'presupuesto' => [
                '¿La compra cabe en mi presupuesto?',
                'PRESUPUESTO',
                '¿La compra cabe en mi presupuesto?',
            ],
            'productos' => [
                '¿Están todos los productos disponibles?',
                'PRODUCTOS',
                '¿Están todos los productos disponibles?',
            ],
            'distancia' => ['¿Qué tan lejos queda esta tienda?', 'DISTANCIA', '¿Cuál es la distancia?'],
            'tiempo' => ['¿Cuánto tiempo tardo en llegar?', 'TIEMPO', '¿Cuánto tiempo tardo en llegar?'],
            'promociones' => ['¿Hay promociones aplicables?', 'PROMOCIONES', '¿Hay promociones aplicables?'],
        ];
    }

    /**
     * Variantes naturales que el clasificador del experto confundía.
     */
    #[DataProvider('variantes')]
    public function test_reconoce_variantes_naturales(string $mensaje, string $intent): void
    {
        $this->assertSame($intent, $this->normalizer->normalizar($mensaje)['intent']);
    }

    public static function variantes(): array
    {
        return [
            'distancia en kilómetros' => ['¿Cuántos kilómetros hay que recorrer?', 'DISTANCIA'],
            'distancia coloquial' => ['¿Queda muy lejos la sucursal?', 'DISTANCIA'],
            'presupuesto con sobra' => ['¿Cuánto me falta o me sobra del presupuesto?', 'PRESUPUESTO'],
            'presupuesto coloquial' => ['¿Me alcanza la plata?', 'PRESUPUESTO'],
            'promociones y ahorro' => ['¿Las promociones mejoran el ahorro?', 'PROMOCIONES'],
            'productos faltantes' => ['¿Qué productos me faltan?', 'PRODUCTOS'],
            'tiempo rápido' => ['¿Es rápido llegar a esta tienda?', 'TIEMPO'],
            'explicación directa' => ['Explicame esta recomendación', 'EXPLICACION'],
            'sin tildes ni mayúsculas' => ['CUANTO ME AHORRO', 'AHORRO'],
        ];
    }

    /**
     * Las preguntas fuera de alcance no deben reescribirse: el experto decide
     * y responde AYUDA.
     */
    #[DataProvider('fueraDeAlcance')]
    public function test_no_reescribe_preguntas_fuera_de_alcance(string $mensaje): void
    {
        $resultado = $this->normalizer->normalizar($mensaje);

        $this->assertNull($resultado['intent']);
        $this->assertSame($mensaje, $resultado['message']);
        $this->assertFalse($resultado['rewritten']);
    }

    public static function fueraDeAlcance(): array
    {
        return [
            'supermercado vago' => ['¿Cuál es el mejor supermercado?'],
            'historial de gastos' => ['¿Cuánto gasté el mes pasado?'],
            'otro supermercado' => ['¿Hay otro supermercado mejor?'],
            'saludo' => ['Hola'],
        ];
    }
}
