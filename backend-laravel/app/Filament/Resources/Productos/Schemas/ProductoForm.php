<?php

namespace App\Filament\Resources\Productos\Schemas;

use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Schema;

class ProductoForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                Select::make('categoria_id')
                    ->label('Categoría')
                    ->relationship('categoria', 'nombre')
                    ->searchable()
                    ->preload()
                    ->required(),
                TextInput::make('marca')
                    ->label('Marca')
                    ->required()
                    ->maxLength(100)
                    ->default('Sin marca'),
                TextInput::make('nombre')
                    ->label('Nombre del producto')
                    ->required()
                    ->maxLength(170)
                    ->columnSpanFull()
                    ->hint('Usa el formato del catálogo: nombre + contenido + presentación'),
                TextInput::make('presentacion')
                    ->label('Presentación')
                    ->maxLength(100)
                    ->placeholder('Lata, Bolsa, Pet...'),
                TextInput::make('unidad_medida')
                    ->label('Unidad de medida')
                    ->maxLength(20)
                    ->placeholder('g, mL, u'),
                TextInput::make('contenido')
                    ->label('Contenido numérico')
                    ->numeric()
                    ->minValue(0)
                    ->helperText('Ej: 216 para "216 g"'),
                Toggle::make('activo')
                    ->label('Activo')
                    ->default(true)
                    ->columnSpanFull(),
            ]);
    }
}
