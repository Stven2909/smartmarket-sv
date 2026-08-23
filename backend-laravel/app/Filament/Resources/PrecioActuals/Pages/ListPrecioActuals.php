<?php

namespace App\Filament\Resources\PrecioActuals\Pages;

use App\Filament\Resources\PrecioActuals\PrecioActualResource;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;

class ListPrecioActuals extends ListRecords
{
    protected static string $resource = PrecioActualResource::class;

    protected function getHeaderActions(): array
    {
        return [
            CreateAction::make(),
        ];
    }
}
