<?php

namespace App\Filament\Widgets;

use App\Models\PrecioActual;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Models\Sucursal;
use Filament\Widgets\StatsOverviewWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class EstadisticasGenerales extends StatsOverviewWidget
{
    protected ?string $heading = 'Estado general';

    protected function getStats(): array
    {
        return [
            Stat::make('Productos activos', Producto::where('activo', true)->count())
                ->description('Catálogo publicado en la API')
                ->color('success'),
            Stat::make('Precios actualizados hoy', PrecioActual::whereDate('fecha_actualizacion', today())->count())
                ->color('info'),
            Stat::make('Staging pendiente', ProductoRaw::where('estado', 'pendiente')->count())
                ->description('Registros por curar del extractor')
                ->color('warning'),
            Stat::make('Sucursales', Sucursal::count())
                ->description('Físicas + tienda en línea'),
        ];
    }
}
