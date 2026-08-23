<?php

namespace App\Filament\Resources\Supermercados\Pages;

use App\Filament\Resources\Supermercados\SupermercadoResource;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditSupermercado extends EditRecord
{
    protected static string $resource = SupermercadoResource::class;

    protected function getHeaderActions(): array
    {
        return [
            DeleteAction::make(),
        ];
    }
}
