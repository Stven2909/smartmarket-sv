<?php

namespace App\Services\PriceProviders;

use App\Services\PriceProviders\Contracts\PriceProvider;
use App\Services\PriceProviders\Support\PoliteHttpClient;
use DOMDocument;
use DOMNode;
use DOMXPath;
use RuntimeException;

// Driver HTML para Super Selectos (la única cadena independiente que no corre
// sobre VTEX).
//
// Selectores verificados contra captura fresca del 2026-08-22
// (tests/fixtures/super-selectos-home.html — los del repo hermano siguen vigentes):
//   - tarjeta:   .producto-box
//   - nombre:    h5.prod-nombre
//   - precio:    .precios strong.precio     (ej. "$1.80")
//   - anterior:  .precios span.antes        (presente solo en promo; el contenedor
//                                           además lo marca con data-hassaving)
//   - URL:       href del primer enlace de la tarjeta (?productId=N)
//
// Mejora sobre la heurística min/max del repo hermano §2.3: cuando hay promo el
// sitio expone el precio anterior de forma explícita — se usa esa señal primero
// y la heurística queda como comportamiento natural (sin .antes no hay promo).
//
// Alcance MVP: recorre las URLs de listado configuradas en la fuente
// ('urls_listado'); paginación profunda de categorías queda para una iteración
// posterior. Solo datos fácticos (ADR-10): la imagen de la tarjeta no se extrae.
class SuperSelectosProvider implements PriceProvider
{
    public function __construct(
        private readonly string $fuente,
        private readonly string $baseUrl,
        private readonly PoliteHttpClient $http,
        private readonly array $urlsListado = [],
    ) {}

    public function fuente(): string
    {
        return $this->fuente;
    }

    public function modo(): string
    {
        return 'html';
    }

    public function traer(): \Generator
    {
        foreach ($this->urlsListado ?: [$this->baseUrl] as $url) {
            yield from $this->productosDePagina((string) $url);
        }
    }

    private function productosDePagina(string $url): \Generator
    {
        $respuesta = $this->http->get($url);

        if (! $respuesta->successful()) {
            throw new RuntimeException("No se pudo descargar el listado de '{$this->fuente}' ({$url}, HTTP {$respuesta->status()}).");
        }

        $xpath = $this->xpathDe($respuesta->body());

        $tarjetas = $xpath->query('//' . $this->selectorPorClase('producto-box'));

        foreach ($tarjetas ?: [] as $tarjeta) {
            $fila = $this->mapearTarjeta($xpath, $tarjeta, $url);

            if ($fila !== null) {
                yield $fila;
            }
        }
    }

    private function mapearTarjeta(DOMXPath $xpath, DOMNode $tarjeta, string $urlPagina): ?array
    {
        $nodoNombre = $xpath->query('.//' . $this->selectorPorClase('prod-nombre'), $tarjeta)?->item(0);
        $nombre = $nodoNombre ? $this->textoLimpio($nodoNombre->textContent) : '';

        // Validación dura del repo hermano §2.5: nombre entre 3 y 220 caracteres.
        if (mb_strlen($nombre) < 3 || mb_strlen($nombre) > 220) {
            return null;
        }

        $precioFinal = null;
        $precioAnterior = null;

        $bloquePrecios = $xpath->query('.//' . $this->selectorPorClase('precios'), $tarjeta)?->item(0);

        if ($bloquePrecios) {
            $precioFinal = $this->extraerPrecio(
                $xpath->query('.//' . $this->selectorPorClase('precio'), $bloquePrecios)?->item(0)?->textContent ?? ''
            );

            $precioAnterior = $this->extraerPrecio(
                $xpath->query('.//' . $this->selectorPorClase('antes'), $bloquePrecios)?->item(0)?->textContent ?? ''
            );
        }

        // Sin precio legible no hay nada que comparar.
        if ($precioFinal === null || $precioFinal <= 0) {
            return null;
        }

        $hayPromo = $precioAnterior !== null && $precioAnterior > $precioFinal;

        return [
            'nombre' => $nombre,
            'unidad' => $this->unidadDesdeNombre($nombre),
            'categoria_raw' => null, // el listado no expone la categoría de la tarjeta
            'precio_normal' => $hayPromo ? round($precioAnterior, 2) : null,
            'precio_final' => round($precioFinal, 2),
            'tiene_promocion' => $hayPromo,
            'disponible' => true, // el listado solo muestra productos comprables
            'url_fuente' => $this->urlTarjeta($xpath, $tarjeta),
            'raw_payload' => [
                'pagina_origen' => $urlPagina,
                'nombre_extraido' => $nombre,
                'precio_actual_texto' => '$' . number_format($precioFinal, 2),
                'precio_anterior_texto' => $precioAnterior !== null ? '$' . number_format($precioAnterior, 2) : null,
                'capturado_en' => now()->toIso8601String(),
            ],
        ];
    }

    private function urlTarjeta(DOMXPath $xpath, DOMNode $tarjeta): ?string
    {
        $href = trim($xpath->query('.//a[@href]', $tarjeta)?->item(0)?->attributes?->getNamedItem('href')?->nodeValue ?? '');

        if ($href === '') {
            return null;
        }

        // Enlaces relativos resueltos contra la base (patrón urljoin del repo hermano).
        if (str_starts_with($href, '/')) {
            return rtrim($this->baseUrl, '/') . $href;
        }

        return $href;
    }

    /**
     * Extrae la unidad métrica final del nombre (ej. "Chocolate Snickers 52.7 g
     * Barra" → "52.7 g"; "Vino ... 750mL" → "750 ml"). Ignora empaques (pack,
     * latas, rollos): solo kg/g/ml/l. Null si no hay patrón claro.
     */
    private function unidadDesdeNombre(string $nombre): ?string
    {
        preg_match_all('/(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l)\b/i', $nombre, $coincidencias, PREG_SET_ORDER);

        if ($coincidencias === []) {
            return null;
        }

        $ultima = end($coincidencias);
        $valor = str_replace(',', '.', $ultima[1]);

        return strtolower($valor . ' ' . $ultima[2]);
    }

    private function extraerPrecio(string $texto): ?float
    {
        if (preg_match('/\$\s*([\d][\d.,]*)/', $texto, $coincidencias) !== 1) {
            return null;
        }

        $numero = str_replace(',', '', $coincidencias[1]);

        return is_numeric($numero) ? (float) $numero : null;
    }

    private function textoLimpio(string $texto): string
    {
        return trim(preg_replace('/\s+/', ' ', $texto) ?? '');
    }

    // Clases compuestas seguras: contains(concat(' ', @class, ' '), ' clase ')
    private function selectorPorClase(string $clase): string
    {
        return sprintf("*[contains(concat(' ', normalize-space(@class), ' '), ' %s ')]", $clase);
    }

    private function xpathDe(string $html): DOMXPath
    {
        $documento = new DOMDocument();

        libxml_use_internal_errors(true);
        // Prefijo XML para forzar lectura UTF-8 del HTML (trick estándar de DOMDocument).
        $documento->loadHTML('<?xml encoding="UTF-8">' . $html);
        libxml_clear_errors();

        return new DOMXPath($documento);
    }
}
