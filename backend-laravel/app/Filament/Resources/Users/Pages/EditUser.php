<?php

namespace App\Filament\Resources\Users\Pages;

use App\Filament\Resources\Users\UserResource;
use Filament\Actions\DeleteAction;
use Filament\Resources\Pages\EditRecord;

class EditUser extends EditRecord
{
    protected static string $resource = UserResource::class;

    protected function getHeaderActions(): array
    {
        return [
            // Un administrador no puede eliminar su propia cuenta desde el panel:
            // evita quedarse sin ninguna cuenta admin con acceso.
            DeleteAction::make()
                ->visible(fn (): bool => auth()->id() !== $this->getRecord()->getKey()),
        ];
    }
}
