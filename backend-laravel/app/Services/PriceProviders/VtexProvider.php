<?php

namespace App\Services\PriceProviders;

use App\Services\PriceProviders\Contracts\PriceProvider;
use App\Services\PriceProviders\Support\PoliteHttpClient;
use RuntimeException;

// Driver genérico para tiendas VTEX (Walmart SV, Maxi Despensa y Don Juan —
// una sola implementación parametrizada por base_url desde
// config/price_providers.php).
//
// Estrategia documentada en docs/06-referencia-extractor-vtex.md §2.2:
//   1. árbol de categorías → solo hojas,
//   2. paginación de productos por categoría (50 por página, total real en el
//      header 'resources'),
//   3. mejor oferta = mínimo Price > 0 entre items×sellers; ListPrice como
//      precio_normal SOLO cuando es mayor al precio final.
//
// Política ADR-10: la imagen y demás contenido creativo que traiga la API no se
// promueve a columnas — queda únicamente dentro de raw_payload como evidencia.
class VtexProvider implements PriceProvider
{
    private const TAM_PAGINA = 50;
    private const PROFUNDIDAD_ARBOL = 10;

    public function __construct(
        private readonly string $fuente,
        private readonly string $baseUrl,
        private readonly PoliteHttpClient $http,
    ) {}

    public function fuente(): string
    {
        return $this->fuente;
    }

    public function modo(): string
    {
        return 'vtex';
    }

    public function traer(): \Generator
    {
        foreach ($this->categoriasHoja() as $categoriaId => $categoriaNombre) {
            yield from $this->productosDeCategoria($categoriaId, $categoriaNombre);
        }
    }

    /** @return \Generator<string, string> id => nombre de las categorías hoja */
    private function categoriasHoja(): \Generator
    {
        $respuesta = $this->http->get(
            $this->url('/api/catalog_system/pub/category/tree/' . self::PROFUNDIDAD_ARBOL)
        );

        if (! $respuesta->successful()) {
            throw new RuntimeException("No se pudo obtener el árbol de categorías de '{$this->fuente}' (HTTP {$respuesta->status()}).");
        }

        yield from $this->recorrerHojas($respuesta->json() ?? []);
    }

    private function recorrerHojas(array $nodos): \Generator
    {
        foreach ($nodos as $nodo) {
            $hijos = $nodo['children'] ?? [];

            // Hoja: sin hijos es donde VTEX lista los productos.
            if ($hijos === []) {
                yield (string) ($nodo['id'] ?? '') => (string) ($nodo['name'] ?? '');
                continue;
            }

            yield from $this->recorrerHojas($hijos);
        }
    }

    private function productosDeCategoria(string $categoriaId, string $categoriaNombre): \Generator
    {
        if ($categoriaId === '') {
            return;
        }

        $total = null;
        $desde = 0;

        while ($total === null || $desde < $total) {
            $respuesta = $this->http->get($this->url('/api/catalog_system/pub/products/search'), [
                'fq' => 'C:' . $categoriaId,
                '_from' => $desde,
                '_to' => $desde + self::TAM_PAGINA - 1,
            ]);

            if (! $respuesta->successful()) {
                throw new RuntimeException(
                    "Error HTTP {$respuesta->status()} listando productos de '{$this->fuente}' (categoría {$categoriaId}, _from={$desde})."
                );
            }

            $productos = $respuesta->json() ?? [];

            if ($total === null) {
                $total = $this->totalDesdeHeader($respuesta);
            }

            // Categoría vacía o la paginación terminó antes del total declarado.
            if ($productos === []) {
                break;
            }

            foreach ($productos as $producto) {
                $fila = $this->mapearProducto($producto, $categoriaNombre);

                if ($fila !== null) {
                    yield $fila;
                }
            }

            $desde += self::TAM_PAGINA;
        }
    }

    // El header 'resources' de VTEX trae el total real de resultados al final.
    private function totalDesdeHeader($respuesta): ?int
    {
        preg_match('/(\d+)\s*$/', (string) $respuesta->header('resources'), $coincidencias);

        return isset($coincidencias[1]) ? (int) $coincidencias[1] : null;
    }

    private function mapearProducto(array $producto, string $categoriaNombre): ?array
    {
        $mejorOferta = $this->mejorOferta($producto['items'] ?? []);

        // Sin oferta válida no hay nada que comparar: se descarta el producto.
        if ($mejorOferta === null || $mejorOferta['precioFinal'] <= 0) {
            return null;
        }

        return [
            'nombre' => trim((string) ($producto['productName'] ?? '')),
            'unidad' => $this->unidad($producto),
            'categoria_raw' => $categoriaNombre !== '' ? $categoriaNombre : trim((string) ($producto['categoryName'] ?? '')),
            'precio_normal' => $mejorOferta['precioLista'],
            'precio_final' => round($mejorOferta['precioFinal'], 2),
            'tiene_promocion' => $mejorOferta['precioLista'] !== null,
            'disponible' => $mejorOferta['availableQuantity'] > 0,
            'url_fuente' => $this->urlProducto($producto),
            'raw_payload' => $producto,
        ];
    }

    /**
     * Oferta de MENOR precio entre todos los items×sellers con Price > 0.
     * El precio de lista (ListPrice) solo cuenta cuando supera al final:
     * eso marca un descuento real (misma heurística del repo hermano §2.2).
     */
    private function mejorOferta(array $items): ?array
    {
        $mejor = null;

        foreach ($items as $item) {
            foreach ($item['sellers'] ?? [] as $seller) {
                $oferta = $seller['commertialOffer'] ?? [];
                $precio = (float) ($oferta['Price'] ?? 0);

                if ($precio <= 0) {
                    continue;
                }

                if ($mejor === null || $precio < $mejor['precioFinal']) {
                    $lista = (float) ($oferta['ListPrice'] ?? 0);

                    $mejor = [
                        'precioFinal' => $precio,
                        'precioLista' => $lista > $precio ? round($lista, 2) : null,
                        'availableQuantity' => (int) ($oferta['AvailableQuantity'] ?? 0),
                    ];
                }
            }
        }

        return $mejor;
    }

    private function unidad(array $producto): ?string
    {
        $medida = trim((string) ($producto['measurementUnit'] ?? ''));

        if ($medida === '') {
            return null;
        }

        $multiplicador = (float) ($producto['unitMultiplier'] ?? 1);

        if ($multiplicador == 1.0) {
            return $medida;
        }

        $multiplicadorLegible = $multiplicador == (int) $multiplicador
            ? (string) (int) $multiplicador
            : (string) $multiplicador;

        return $multiplicadorLegible . ' ' . $medida;
    }

    private function urlProducto(array $producto): ?string
    {
        $linkText = trim((string) ($producto['linkText'] ?? ''));

        return $linkText === '' ? null : $this->url('/' . $linkText . '/p');
    }

    private function url(string $ruta): string
    {
        return rtrim($this->baseUrl, '/') . $ruta;
    }
}
