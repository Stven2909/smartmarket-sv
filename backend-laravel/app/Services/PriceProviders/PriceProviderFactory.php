<?php

namespace App\Services\PriceProviders;

use App\Services\PriceProviders\Contracts\PriceProvider;
use App\Services\PriceProviders\Support\PoliteHttpClient;
use InvalidArgumentException;

// Resuelve la clave de fuente (config/price_providers.php) hacia su driver.
// Las fuentes manuales y los modos sin driver lanzan InvalidArgumentException:
// nunca inventamos un driver para una fuente que no lo tiene (ADR-10).
class PriceProviderFactory
{
    public function __construct(private readonly PoliteHttpClient $http) {}

    public function hacer(string $fuente): PriceProvider
    {
        $fuentes = config('price_providers.fuentes', []);

        if (! isset($fuentes[$fuente])) {
            throw new InvalidArgumentException(
                "Fuente desconocida '{$fuente}'. Fuentes definidas: " . implode(', ', array_keys($fuentes))
            );
        }

        $config = $fuentes[$fuente];
        $modo = (string) ($config['modo'] ?? '');

        if ($modo === 'manual') {
            throw new InvalidArgumentException("La fuente '{$fuente}' es de carga manual y no tiene driver automático (ADR-10).");
        }

        return match ($modo) {
            'vtex' => new VtexProvider($fuente, (string) $config['base_url'], $this->http),
            'html' => new SuperSelectosProvider(
                $fuente,
                (string) $config['base_url'],
                $this->http,
                (array) ($config['urls_listado'] ?? []),
            ),
            default => throw new InvalidArgumentException("Modo '{$modo}' sin soporte para la fuente '{$fuente}'."),
        };
    }
}
