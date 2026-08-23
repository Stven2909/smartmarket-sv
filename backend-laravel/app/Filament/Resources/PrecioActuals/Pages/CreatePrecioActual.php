<?php

namespace App\Filament\Resources\PrecioActuals\Pages;

use App\Filament\Resources\PrecioActuals\PrecioActualResource;
use Filament\Resources\Pages\CreateRecord;

class CreatePrecioActual extends CreateRecord
{
    protected static string $resource = PrecioActualResource::class;

    protected function mutateFormDataBeforeCreate(array $data): array
    {
        // Carga manual: sellamos frescura y origen aca en lugar de pedirselos
        // al admin — el campo origen_dato distingue estos precios de los del
        // extractor (que usa el patron {modo}-{fuente}, ej. html-super-selectos).
        $data['origen_dato'] = 'manual';
        $data['fecha_actualizacion'] = now();

        return $data;
    }
}
