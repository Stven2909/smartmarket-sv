<?php

namespace App\Filament\Resources\Supermercados\Pages;

use App\Filament\Resources\Supermercados\SupermercadoResource;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;

class ListSupermercados extends ListRecords
{
    protected static string $resource = SupermercadoResource::class;

    protected function getHeaderActions(): array
    {
        return [
            CreateAction::make(),
        ];
    }
}
