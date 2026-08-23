<?php

namespace App\Console\Commands;

use App\Models\ProductoRaw;
use App\Models\SyncRun;
use App\Services\NormalizadorTexto;
use App\Services\PriceProviders\Contracts\PriceProvider;
use App\Services\PriceProviders\Exceptions\FuenteBloqueadaException;
use App\Services\PriceProviders\PriceProviderFactory;
use Illuminate\Console\Command;
use InvalidArgumentException;
use Throwable;

// Price Provider del Flujo 2 (02-arquitectura.md §6): obtiene → valida →
// escribe SOLO a staging (producto_raw), jamás directo a precios_actuales.
//
// Cortesía y postura según ADR-10; health check por corrida según
// 06-referencia-extractor-vtex.md §4 punto 5.
class PreciosSync extends Command
{
    protected $signature = 'precios:sync
        {--fuente= : Clave de la fuente (ej. walmart). Vacío = todas las habilitadas}
        {--limite= : Tope de productos obtenidos por fuente (útil para pruebas)}
        {--dry-run : Recolecta y reporta sin escribir en staging}';

    protected $description = 'Sincroniza precios desde las fuentes habilitadas hacia la zona de staging (producto_raw)';

    // Caída brusca: menos del 70% de los productos de la corrida exitosa previa.
    private const UMBRAL_CAIDA_SALUDABLE = 0.7;

    // Validaciones duras del repo hermano §2.5.
    private const NOMBRE_MIN = 3;
    private const NOMBRE_MAX = 220;
    private const PRECIO_MAX = 100000.0;

    public function handle(PriceProviderFactory $factory): int
    {
        $claves = $this->fuentesObjetivo();

        if ($claves === null) {
            return self::FAILURE;
        }

        if ($claves === []) {
            $this->warn('No hay fuentes habilitadas para sincronizar.');

            return self::SUCCESS;
        }

        $huboFallos = false;

        foreach ($claves as $clave) {
            try {
                $provider = $factory->hacer($clave);
            } catch (InvalidArgumentException $e) {
                $this->warn("[{$clave}] {$e->getMessage()}");

                continue;
            }

            if (! $this->sincronizarFuente($provider)) {
                $huboFallos = true;
            }
        }

        return $huboFallos ? self::FAILURE : self::SUCCESS;
    }

    // null = opción inválida; [] = nada que hacer; [claves] = objetivo.
    private function fuentesObjetivo(): ?array
    {
        $todas = config('price_providers.fuentes', []);

        if ($clave = $this->option('fuente')) {
            if (! isset($todas[$clave])) {
                $this->error("Fuente desconocida '{$clave}'. Definidas: " . implode(', ', array_keys($todas)));

                return null;
            }

            return [$clave];
        }

        return collect($todas)
            ->filter(fn ($config) => $config['enabled'] ?? false)
            ->keys()
            ->all();
    }

    private function sincronizarFuente(PriceProvider $provider): bool
    {
        $fuente = $provider->fuente();
        $esDryRun = (bool) $this->option('dry-run');
        $limite = max(0, (int) $this->option('limite'));

        $run = SyncRun::create([
            'fuente' => $fuente,
            'modo' => $provider->modo(),
            'estado' => 'en_curso',
            'iniciada_en' => now(),
        ]);

        $vistosEnCorrida = [];
        $motivosRechazo = [];
        $obtenidos = 0;
        $nuevos = 0;
        $duplicados = 0;
        $rechazados = 0;

        try {
            foreach ($provider->traer() as $fila) {
                if ($limite > 0 && $obtenidos >= $limite) {
                    break;
                }

                $sku = hash(
                    'sha256',
                    NormalizadorTexto::limpiar((string) ($fila['nombre'] ?? ''))
                    . '|' . NormalizadorTexto::limpiar((string) ($fila['unidad'] ?? '')),
                );

                // Deduplicación intra-corrida (misma clave canónica dos veces).
                if (isset($vistosEnCorrida[$sku])) {
                    $duplicados++;

                    continue;
                }
                $vistosEnCorrida[$sku] = true;

                if ($motivo = $this->motivoDeRechazo($fila)) {
                    $rechazados++;
                    $motivosRechazo[$motivo] = ($motivosRechazo[$motivo] ?? 0) + 1;

                    continue;
                }

                $existe = ProductoRaw::where('fuente', $fuente)->where('sku_externo', $sku)->exists();

                if (! $esDryRun) {
                    ProductoRaw::updateOrCreate(
                        ['fuente' => $fuente, 'sku_externo' => $sku],
                        [
                            'nombre' => $fila['nombre'],
                            'unidad' => $fila['unidad'] ?? null,
                            'categoria_raw' => $fila['categoria_raw'] ?? null,
                            'precio_normal' => $fila['precio_normal'] ?? null,
                            'precio_final' => $fila['precio_final'],
                            'tiene_promocion' => (bool) ($fila['tiene_promocion'] ?? false),
                            'disponible' => $fila['disponible'] ?? null,
                            'url_fuente' => $fila['url_fuente'] ?? null,
                            'raw_payload' => $fila['raw_payload'] ?? [],
                            // Re-colectado vuelve a la cola de procesamiento.
                            'estado' => 'pendiente',
                            'motivo_rechazo' => null,
                            'sync_run_id' => $run->id,
                        ],
                    );
                }

                $obtenidos++;
                $existe ? $duplicados++ : $nuevos++;
            }
        } catch (FuenteBloqueadaException $e) {
            $this->finalizarRun($run, 'abortada', $obtenidos, $nuevos, $duplicados, $rechazados, $motivosRechazo, $e->getMessage());

            $this->error("[{$fuente}] ABORTADA — {$e->getMessage()}");

            return false;
        } catch (Throwable $e) {
            $this->finalizarRun($run, 'fallida', $obtenidos, $nuevos, $duplicados, $rechazados, $motivosRechazo, $e->getMessage());

            $this->error("[{$fuente}] FALLIDA — {$e->getMessage()}");

            return false;
        }

        $alertas = $this->alertasDeSalud($fuente, $obtenidos, $run->id);

        $this->finalizarRun($run, 'exitosa', $obtenidos, $nuevos, $duplicados, $rechazados, $motivosRechazo, null, $alertas);

        foreach ($alertas as $alerta) {
            $this->warn("[{$fuente}] ALERTA DE SALUD — {$alerta}");
        }

        $sufijoDry = $esDryRun ? ' (dry-run: sin escritura)' : '';

        $this->info("[{$fuente}] exitosa — obtenidos={$obtenidos} nuevos={$nuevos} duplicados={$duplicados} rechazados={$rechazados}{$sufijoDry}");

        return true;
    }

    private function motivoDeRechazo(array $fila): ?string
    {
        $largoNombre = mb_strlen(trim((string) ($fila['nombre'] ?? '')));

        if ($largoNombre < self::NOMBRE_MIN || $largoNombre > self::NOMBRE_MAX) {
            return 'nombre_invalido';
        }

        $precioFinal = $fila['precio_final'] ?? null;

        if (! is_numeric($precioFinal) || $precioFinal <= 0 || $precioFinal > self::PRECIO_MAX) {
            return 'precio_fuera_de_rango';
        }

        if (($precioNormal = $fila['precio_normal'] ?? null) !== null
            && (! is_numeric($precioNormal) || $precioNormal < $precioFinal)) {
            return 'precio_normal_menor_al_final';
        }

        if (! empty($fila['url_fuente']) && ! str_starts_with((string) $fila['url_fuente'], 'https://')) {
            return 'url_no_https';
        }

        return null;
    }

    /** @return string[] */
    private function alertasDeSalud(string $fuente, int $obtenidos, int $runIdActual): array
    {
        $previaExitosa = SyncRun::where('fuente', $fuente)
            ->where('estado', 'exitosa')
            ->where('id', '!=', $runIdActual)
            ->orderByDesc('id')
            ->first();

        if (! $previaExitosa || $previaExitosa->productos_obtenidos < 100) {
            return [];
        }

        if ($obtenidos < (int) round($previaExitosa->productos_obtenidos * self::UMBRAL_CAIDA_SALUDABLE)) {
            return [
                "Caída brusca: {$obtenidos} obtenidos vs {$previaExitosa->productos_obtenidos} en la corrida previa. Revisar antes de publicar.",
            ];
        }

        return [];
    }

    private function finalizarRun(
        SyncRun $run,
        string $estado,
        int $obtenidos,
        int $nuevos,
        int $duplicados,
        int $rechazados,
        array $motivosRechazo,
        ?string $mensajeError,
        array $alertas = [],
    ): void {
        $run->update([
            'estado' => $estado,
            'finalizada_en' => now(),
            'productos_obtenidos' => $obtenidos,
            'productos_nuevos' => $nuevos,
            'productos_duplicados' => $duplicados,
            'rechazados' => $rechazados,
            'detalle' => array_filter([
                'motivos_rechazo' => $motivosRechazo ?: null,
                'alertas' => $alertas ?: null,
            ]),
            'mensaje_error' => $mensajeError,
        ]);
    }
}
