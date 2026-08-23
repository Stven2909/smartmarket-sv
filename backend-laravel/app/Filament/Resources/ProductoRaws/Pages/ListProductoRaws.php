<?php

namespace App\Filament\Resources\ProductoRaws\Pages;

use App\Filament\Resources\ProductoRaws\ProductoRawResource;
use Filament\Actions\CreateAction;
use Filament\Resources\Pages\ListRecords;

class ListProductoRaws extends ListRecords
{
    protected static string $resource = ProductoRawResource::class;

    protected function getHeaderActions(): array
    {
        return [
            CreateAction::make(),
        ];
    }
}
