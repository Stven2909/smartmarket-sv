<?php

namespace App\Console\Commands;

use App\Services\PriceProviders\StagingProcessor;
use Illuminate\Console\Command;

// Segundo tramo del Flujo 2 (02-arquitectura.md §6): toma producto_raw y lo
// normaliza hacia el Catálogo Maestro. Separado de precios:sync para que la
// recolección (que habla con internet) y la publicación (local, idempotente)
// se ejecuten — y fallen — de forma independiente.
//
// Alcance operativo (ADR-012): solo Super Selectos deja filas en staging. El
// comando usa esa fuente por defecto y rechaza cualquier otra; las demás
// cadenas se alimentan desde MockSupermarketsSeeder.
class PreciosProcesar extends Command
{
    protected $signature = 'precios:procesar
        {--fuente= : Clave de la fuente (solo super-selectos). Vacío = fuente por defecto}
        {--limite= : Tope de filas a procesar en esta corrida}
        {--dry-run : Simula el matching y reporta sin escribir}';

    protected $description = 'Publica los precios de staging (producto_raw) hacia el catálogo: matching por alias, upsert en precios_actuales y append al historial';

    public function handle(StagingProcessor $processor): int
    {
        $todas = config('price_providers.fuentes', []);
        $permitidas = $this->fuentesPermitidas();

        $fuente = (string) ($this->option('fuente')
            ?: config('price_providers.sincronizacion.fuente_por_defecto', ''));

        if ($fuente === '') {
            $this->error('No hay fuente por defecto configurada en price_providers.sincronizacion.fuente_por_defecto.');

            return self::FAILURE;
        }

        if (! array_key_exists($fuente, $todas)) {
            $this->error("Fuente desconocida '{$fuente}'. Definidas: " . implode(', ', array_keys($todas)));

            return self::FAILURE;
        }

        if (! in_array($fuente, $permitidas, true)) {
            $this->error("La fuente '{$fuente}' no está habilitada para procesamiento. Solo se permite: "
                . (implode(', ', $permitidas) ?: 'ninguna')
                . '. Las demás cadenas usan datos mock (ADR-012).');

            return self::FAILURE;
        }

        $conteos = $processor->procesar(
            $fuente,
            max(0, (int) $this->option('limite')),
            (bool) $this->option('dry-run'),
        );

        $sufijoDry = $this->option('dry-run') ? ' (dry-run: sin escritura)' : '';

        $etiqueta = $fuente;

        $this->info("[{$etiqueta}] procesados={$conteos['procesados']}"
            . " publicados={$conteos['publicados']}"
            . " nuevos_productos={$conteos['nuevos_productos']}"
            . " alias_nuevos={$conteos['alias_nuevos']}"
            . " revision_manual={$conteos['revision_manual']}"
            . " errores={$conteos['errores']}"
            . "{$sufijoDry}");

        // Los errores individuales ya quedaron marcados en staging con su motivo:
        // la corrida no se considera fallida por ellos.
        return self::SUCCESS;
    }

    /** @return string[] */
    private function fuentesPermitidas(): array
    {
        $permitidas = config('price_providers.sincronizacion.fuentes_permitidas', []);

        return is_array($permitidas) ? array_values($permitidas) : [];
    }
}
