<?php

namespace App\Filament\Resources\PrecioActuals\Pages;

use App\Filament\Resources\PrecioActuals\PrecioActualResource;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditPrecioActual extends EditRecord
{
    protected static string $resource = PrecioActualResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }

    protected function mutateFormDataBeforeSave(array $data): array
    {
        // Toda edicion refresca la fecha: si el cambio toca precios, el
        // PrecioActualObserver ya archivo el valor anterior en historial;
        // esta fecha marca cuando el humano confirmo el nuevo valor.
        $data['fecha_actualizacion'] = now();

        return $data;
    }
}
