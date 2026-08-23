<?php

namespace App\Console\Commands;

use App\Services\PriceProviders\StagingProcessor;
use Illuminate\Console\Command;

// Segundo tramo del Flujo 2 (02-arquitectura.md §6): toma producto_raw y lo
// normaliza hacia el Catálogo Maestro. Separado de precios:sync para que la
// recolección (que habla con internet) y la publicación (local, idempotente)
// se ejecuten — y fallen — de forma independiente.
class PreciosProcesar extends Command
{
    protected $signature = 'precios:procesar
        {--fuente= : Clave de la fuente (ej. walmart). Vacío = todas las filas pendientes}
        {--limite= : Tope de filas a procesar en esta corrida}
        {--dry-run : Simula el matching y reporta sin escribir}';

    protected $description = 'Publica los precios de staging (producto_raw) hacia el catálogo: matching por alias, upsert en precios_actuales y append al historial';

    public function handle(StagingProcessor $processor): int
    {
        $fuente = $this->option('fuente') ?: null;

        if ($fuente !== null && ! array_key_exists((string) $fuente, config('price_providers.fuentes', []))) {
            $this->error("Fuente desconocida '{$fuente}'. Definidas: "
                . implode(', ', array_keys(config('price_providers.fuentes', []))));

            return self::FAILURE;
        }

        $conteos = $processor->procesar(
            $fuente !== null ? (string) $fuente : null,
            max(0, (int) $this->option('limite')),
            (bool) $this->option('dry-run'),
        );

        $sufijoDry = $this->option('dry-run') ? ' (dry-run: sin escritura)' : '';

        $etiqueta = $fuente ?? 'todas-las-fuentes';

        $this->info("[{$etiqueta}] procesados={$conteos['procesados']}"
            . " publicados={$conteos['publicados']}"
            . " nuevos_productos={$conteos['nuevos_productos']}"
            . " alias_nuevos={$conteos['alias_nuevos']}"
            . " errores={$conteos['errores']}"
            . "{$sufijoDry}");

        // Los errores individuales ya quedaron marcados en staging con su motivo:
        // la corrida no se considera fallida por ellos.
        return self::SUCCESS;
    }
}
