<?php

namespace App\Filament\Resources\Supermercados\Schemas;

use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Schema;

class SupermercadoForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('nombre')
                    ->label('Nombre')
                    ->required()
                    ->maxLength(150)
                    ->unique(ignoreRecord: true),
                TextInput::make('sitio_web')
                    ->label('Sitio web')
                    ->url()
                    ->maxLength(255)
                    ->placeholder('https://...'),
                TextInput::make('logo')
                    ->label('Logo (URL)')
                    ->url()
                    ->maxLength(255),
                Toggle::make('activo')
                    ->label('Activo')
                    ->default(true)
                    ->helperText('Los supermercados inactivos no participan en nuevas cargas de datos'),
            ]);
    }
}
