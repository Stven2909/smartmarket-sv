<?php

namespace App\Services\PriceProviders;

use App\Models\AliasProducto;
use App\Models\Categoria;
use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Models\Supermercado;
use App\Models\Sucursal;
use App\Services\NormalizadorTexto;
use RuntimeException;
use Throwable;

// Etapa final del Flujo 2 (02-arquitectura.md §6): toma lo crudo de producto_raw
// y lo publica en el Catálogo Maestro mediante el Motor de Normalización (§6.2):
//
//   1. Alias EXACTO (texto normalizado)          → vincula al producto existente.
//   2. Similitud similar_text >= 85%             → vincula al mejor candidato y
//                                                  registra el nombre como alias nuevo.
//   3. Sin coincidencia                          → crea Producto nuevo + su alias.
//
// Después: upsert IDEMPOTENTE en precios_actuales (estado "hoy" por producto+
// sucursal), append SIEMPRE en historial_precios (Regla fija #1 §6.3) y marca la
// fila de staging como publicado/error con trazabilidad completa.
class StagingProcessor
{
    // Umbral aprobado en doc 06 §4: similar_text >= 85% sobre texto normalizado.
    private const UMBRAL_SIMILITUD = 85.0;

    // Si el mejor y el segundo candidato están a menos de este margen (y ambos
    // superan el umbral), el match es ambiguo: no se auto-vincula ni se publica.
    // La fila queda en estado "revision_manual" para que una persona decida.
    private const MARGEN_AMBIGUEDAD = 4.0;

    // Límite físico de la columna productos.nombre (staging admite 220).
    private const NOMBRE_PRODUCTO_MAX = 170;

    // ADR-11: cada supermercado automatizado tiene una sucursal virtual sin
    // coordenadas — el optimizador la excluye del ranking por distancia.
    private const SUCURSAL_ONLINE = 'Tienda en línea';

    /** @var array<string, int> alias normalizado => producto_id */
    private array $indiceAlias = [];

    /** @var array<string, int> nombre normalizado => producto_id */
    private array $indiceNombres = [];

    /** @var array<string, ?string> nombre normalizado => firma de unidad */
    private array $indiceUnidades = [];

    /** @var array<string, true> nombres normalizados que apuntan a más de un producto */
    private array $nombresDuplicados = [];

    /** @var array<string, true> alias normalizados que apuntan a más de un producto */
    private array $aliasDuplicados = [];

    private bool $indicesCargados = false;

    /**
     * Procesa las filas pendientes de staging y devuelve los conteos de la corrida.
     *
     * @return array{procesados: int, publicados: int, nuevos_productos: int, alias_nuevos: int, revision_manual: int, errores: int}
     */
    public function procesar(?string $fuente = null, ?int $limite = null, bool $dryRun = false): array
    {
        $consulta = ProductoRaw::query()
            ->where('estado', 'pendiente')
            ->orderBy('id');

        if ($fuente !== null && $fuente !== '') {
            $consulta->where('fuente', $fuente);
        }

        if ($limite !== null && $limite > 0) {
            $consulta->limit($limite);
        }

        return $this->procesarFilas($consulta->cursor(), $dryRun);
    }

    /**
     * Publica un lote CONCRETO de filas ya seleccionadas (comando artisan o
     * acciones "Publicar" del panel Filament). Misma escalera de matching,
     * mismos conteos y misma trazabilidad de errores que procesar().
     *
     * @param  iterable<ProductoRaw>  $filas
     * @return array{procesados: int, publicados: int, nuevos_productos: int, alias_nuevos: int, revision_manual: int, errores: int}
     */
    public function procesarFilas(iterable $filas, bool $dryRun = false): array
    {
        $this->cargarIndices();

        $conteos = [
            'procesados' => 0,
            'publicados' => 0,
            'nuevos_productos' => 0,
            'alias_nuevos' => 0,
            'revision_manual' => 0,
            'errores' => 0,
        ];

        foreach ($filas as $fila) {
            try {
                $this->procesarFila($fila, $conteos, $dryRun);
            } catch (Throwable $e) {
                $conteos['errores']++;

                // El error queda registrado en la propia fila: nada se pierde
                // silenciosamente y es auditable desde staging.
                if (! $dryRun) {
                    $fila->update([
                        'estado' => 'error',
                        'motivo_rechazo' => mb_substr($e->getMessage(), 0, 255),
                    ]);
                }
            }

            $conteos['procesados']++;
        }

        return $conteos;
    }

    private function procesarFila(ProductoRaw $fila, array &$conteos, bool $dryRun): void
    {
        // Defensa en profundidad: precios:sync ya valida, pero staging puede ser
        // tocado a mano — jamás publicamos un precio que no sirva para comparar.
        if (! is_numeric($fila->precio_final) || (float) $fila->precio_final <= 0) {
            throw new RuntimeException('precio_invalido_en_staging');
        }

        $match = $this->resolverProducto($fila, $conteos, $dryRun);

        // Ambigüedad de catálogo: la fila no se publica ni se descarta. Queda en
        // la cola de revisión con los candidatos que empataron para que una
        // persona resuelva el alias (evita contaminar el catálogo).
        if ($match['motivo_revision'] !== null) {
            $conteos['revision_manual']++;

            if (! $dryRun) {
                $fila->update([
                    'estado' => 'revision_manual',
                    'motivo_rechazo' => mb_substr($match['motivo_revision'], 0, 255),
                    'procesado_at' => now(),
                ]);
            }

            return;
        }

        $productoId = $match['producto_id'];

        if ($dryRun) {
            // Simulación: solo contamos qué pasaría; ningún write toca la base.
            $conteos['publicados']++;

            return;
        }

        if ($productoId === null) {
            throw new RuntimeException('producto_no_resuelto_en_staging');
        }

        $sucursal = $this->sucursalOnline($fila->fuente);
        $origenDato = $this->origenDato($fila);

        // precio_normal es NOT NULL en catálogo: sin promo, lista == final.
        $precioNormal = $fila->precio_normal !== null ? $fila->precio_normal : $fila->precio_final;

        // Convención doc 06 §4 punto 2: '{modo}-{fuente}'.
        // NOTA sobre el historial: NO se inserta aquí a mano. El
        // PrecioActualObserver ya archiva automáticamente el precio ANTERIOR en
        // historial_precios cuando este upsert lo cambia (Regla fija #1 §6.3,
        // tabla append-only) — escribir también aquí duplicaría cada transición.
        // La primera publicación no deja fila de historial: aún no hay precio
        // previo que quede "sin vigencia".
        PrecioActual::updateOrCreate(
            ['producto_id' => $productoId, 'sucursal_id' => $sucursal->id],
            [
                'precio_normal' => $precioNormal,
                'precio_final' => $fila->precio_final,
                'tiene_promocion' => (bool) $fila->tiene_promocion,
                'tipo_promocion' => null,
                'fecha_actualizacion' => now(),
                'origen_dato' => $origenDato,
            ],
        );

        $fila->update([
            'estado' => 'publicado',
            'motivo_rechazo' => null,
            'procesado_at' => now(),
        ]);

        $conteos['publicados']++;
    }

    /**
     * Escalera de matching del Motor de Normalización. Devuelve el producto_id
     * (o null si el dry-run crearía uno nuevo) y, cuando corresponde, el motivo
     * para enviar la fila a revisión manual.
     *
     * @return array{producto_id: ?int, motivo_revision: ?string}
     */
    private function resolverProducto(ProductoRaw $fila, array &$conteos, bool $dryRun): array
    {
        $claveNombre = NormalizadorTexto::limpiar($fila->nombre);

        // 1a. Nombre normalizado exacto. Si dos productos comparten el mismo
        // nombre canónico, el catálogo está duplicado: no se elige uno al azar.
        if (isset($this->indiceNombres[$claveNombre])) {
            if (isset($this->nombresDuplicados[$claveNombre])) {
                return $this->revision(
                    "nombre_normalizado_duplicado: {$claveNombre}",
                );
            }

            $productoId = $this->indiceNombres[$claveNombre];
            $this->registrarAliasSiNuevo($productoId, $claveNombre, $fila, $conteos, $dryRun);

            return $this->resuelto($productoId);
        }

        // 1b. Alias normalizado exacto (incluye aliases sembrados en formato legible).
        if (isset($this->indiceAlias[$claveNombre])) {
            if (isset($this->aliasDuplicados[$claveNombre])) {
                return $this->revision(
                    "alias_normalizado_duplicado: {$claveNombre}",
                );
            }

            $productoId = $this->indiceAlias[$claveNombre];
            $this->registrarAliasSiNuevo($productoId, $claveNombre, $fila, $conteos, $dryRun);

            return $this->resuelto($productoId);
        }

        // 2. Similitud difusa contra los nombres del catálogo: gana el mejor %,
        // pero solo entre candidatos con presentación compatible.
        $firmaRaw = NormalizadorTexto::firmaUnidad($fila->nombre);
        $mejorId = null;
        $mejorPorcentaje = 0.0;
        $segundoId = null;
        $segundoPorcentaje = 0.0;

        foreach ($this->indiceNombres as $nombreNorm => $id) {
            $nombreNorm = (string) $nombreNorm;
            $firmaCandidato = $this->indiceUnidades[$nombreNorm] ?? null;

            // "Leche 1 L" y "Leche 2 L" se parecen mucho, pero no son el mismo
            // producto. Si ambas presentaciones son legibles y difieren, el
            // candidato se descarta antes de calcular similitud.
            if ($firmaRaw !== null && $firmaCandidato !== null && $firmaRaw !== $firmaCandidato) {
                continue;
            }

            similar_text($claveNombre, $nombreNorm, $porcentaje);

            if ($porcentaje > $mejorPorcentaje) {
                $segundoId = $mejorId;
                $segundoPorcentaje = $mejorPorcentaje;
                $mejorPorcentaje = $porcentaje;
                $mejorId = (int) $id;
            } elseif ($porcentaje > $segundoPorcentaje) {
                $segundoPorcentaje = $porcentaje;
                $segundoId = (int) $id;
            }
        }

        $mejorSobreUmbral = $mejorId !== null && $mejorPorcentaje >= self::UMBRAL_SIMILITUD;
        $segundoSobreUmbral = $segundoId !== null
            && $segundoId !== $mejorId
            && $segundoPorcentaje >= self::UMBRAL_SIMILITUD;

        if ($mejorSobreUmbral && $segundoSobreUmbral
            && ($mejorPorcentaje - $segundoPorcentaje) < self::MARGEN_AMBIGUEDAD) {
            $nombreMejor = array_search($mejorId, $this->indiceNombres, true);
            $nombreSegundo = array_search($segundoId, $this->indiceNombres, true);

            return $this->revision(sprintf(
                'match_ambiguo: "%s" (%.1f%%) vs "%s" (%.1f%%)',
                is_string($nombreMejor) ? $nombreMejor : (string) $mejorId,
                $mejorPorcentaje,
                is_string($nombreSegundo) ? $nombreSegundo : (string) $segundoId,
                $segundoPorcentaje,
            ));
        }

        if ($mejorSobreUmbral) {
            $this->registrarAliasSiNuevo($mejorId, $claveNombre, $fila, $conteos, $dryRun);

            return $this->resuelto($mejorId);
        }

        // 3. Producto nuevo del catálogo maestro.
        $conteos['nuevos_productos']++;

        if ($dryRun) {
            // En simulación no persistimos ni contaminamos los índices: cada fila
            // candidata se cuenta de forma independiente.
            return $this->resuelto(null);
        }

        $categoriaOtros = Categoria::firstOrCreate(['nombre' => 'Otros']);

        $producto = Producto::create([
            // Categoría/marca desconocidas por ahora: son campos del ERD NOT NULL,
            // el refinamiento manual o por reglas regex es una iteración posterior.
            'categoria_id' => $categoriaOtros->id,
            'marca' => 'Sin marca',
            'nombre' => mb_substr($fila->nombre, 0, self::NOMBRE_PRODUCTO_MAX),
            'unidad_medida' => mb_substr((string) ($fila->unidad ?? ''), 0, 20) ?: null,
            'contenido' => null,
            'presentacion' => null,
            'activo' => true,
        ]);

        $this->indiceNombres[$claveNombre] = $producto->id;
        $this->indiceUnidades[$claveNombre] = $firmaRaw;
        $this->registrarAliasSiNuevo($producto->id, $claveNombre, $fila, $conteos, $dryRun);

        return $this->resuelto($producto->id);
    }

    /** @return array{producto_id: ?int, motivo_revision: ?string} */
    private function resuelto(?int $productoId): array
    {
        return ['producto_id' => $productoId, 'motivo_revision' => null];
    }

    /** @return array{producto_id: null, motivo_revision: string} */
    private function revision(string $motivo): array
    {
        return ['producto_id' => null, 'motivo_revision' => $motivo];
    }

    private function registrarAliasSiNuevo(int $productoId, string $claveNombre, ProductoRaw $fila, array &$conteos, bool $dryRun): void
    {
        if ($dryRun || isset($this->indiceAlias[$claveNombre])) {
            return;
        }

        AliasProducto::create([
            'producto_id' => $productoId,
            'alias' => $claveNombre,
            'origen' => $fila->fuente,
        ]);

        $this->indiceAlias[$claveNombre] = $productoId;
        $conteos['alias_nuevos']++;
    }

    // Convención doc 06 §4 punto 2: origen_dato = '{modo}-{fuente}'.
    private function origenDato(ProductoRaw $fila): string
    {
        $modo = config("price_providers.fuentes.{$fila->fuente}.modo");

        if (! is_string($modo) || $modo === '') {
            $modo = $fila->syncRun?->modo ?? 'desconocido';
        }

        return $modo . '-' . $fila->fuente;
    }

    /**
     * Sucursal virtual donde aterrizan los precios automáticos de esta fuente
     * (ADR-11): una sola "Tienda en línea" por supermercado, sin coordenadas.
     */
    private function sucursalOnline(string $fuente): Sucursal
    {
        $nombreSupermercado = (string) config("price_providers.fuentes.{$fuente}.supermercado", '');

        if ($nombreSupermercado === '') {
            throw new RuntimeException("supermercado_no_configurado_para_fuente_{$fuente}");
        }

        $supermercado = Supermercado::firstOrCreate(
            ['nombre' => $nombreSupermercado],
            ['activo' => true],
        );

        return Sucursal::firstOrCreate(
            ['supermercado_id' => $supermercado->id, 'nombre' => self::SUCURSAL_ONLINE],
            [
                'direccion' => 'Compra en línea — sin dirección física',
                'latitud' => null,
                'longitud' => null,
                'telefono' => null,
                'horario' => null,
            ],
        );
    }

    private function cargarIndices(): void
    {
        if ($this->indicesCargados) {
            return; // reutilizable dentro de la misma corrida
        }

        foreach (Producto::query()->select('id', 'nombre')->orderBy('id')->cursor() as $producto) {
            $clave = NormalizadorTexto::limpiar($producto->nombre);

            if (isset($this->indiceNombres[$clave])) {
                if ($this->indiceNombres[$clave] !== $producto->id) {
                    $this->nombresDuplicados[$clave] = true;
                }

                continue; // conserva el producto de menor id de forma determinista
            }

            $this->indiceNombres[$clave] = $producto->id;
            $this->indiceUnidades[$clave] = NormalizadorTexto::firmaUnidad($producto->nombre);
        }

        foreach (AliasProducto::query()->select('producto_id', 'alias')->orderBy('id')->cursor() as $alias) {
            $clave = NormalizadorTexto::limpiar($alias->alias);

            if (isset($this->indiceAlias[$clave]) && $this->indiceAlias[$clave] !== $alias->producto_id) {
                $this->aliasDuplicados[$clave] = true;

                continue;
            }

            $this->indiceAlias[$clave] = $alias->producto_id;
        }

        $this->indicesCargados = true;
    }
}
