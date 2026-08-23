<?php

namespace App\Filament\Resources\Sucursals\Schemas;

use Closure;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Utilities\Get;
use Filament\Schemas\Schema;

class SucursalForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                Select::make('supermercado_id')
                    ->label('Supermercado')
                    ->relationship('supermercado', 'nombre')
                    ->searchable()
                    ->preload()
                    ->required(),
                TextInput::make('nombre')
                    ->label('Nombre de la sucursal')
                    ->required()
                    ->maxLength(150),
                TextInput::make('direccion')
                    ->label('Dirección')
                    ->required()
                    ->maxLength(255)
                    ->columnSpanFull()
                    ->placeholder('Para tienda en línea: Compra en línea — sin dirección física'),
                TextInput::make('latitud')
                    ->label('Latitud')
                    ->numeric()
                    ->minValue(-90)
                    ->maxValue(90)
                    ->rules([
                        fn (Get $get): Closure => fn (string $attribute, $value, Closure $fail) => filled($value) !== filled($get('longitud'))
                            ? $fail('Define ambas coordenadas o ninguna.')
                            : null,
                    ])
                    ->helperText('Vacías = canal online sin ubicación física (ADR-11)'),
                TextInput::make('longitud')
                    ->label('Longitud')
                    ->numeric()
                    ->minValue(-180)
                    ->maxValue(180)
                    ->rules([
                        fn (Get $get): Closure => fn (string $attribute, $value, Closure $fail) => filled($value) !== filled($get('latitud'))
                            ? $fail('Define ambas coordenadas o ninguna.')
                            : null,
                    ]),
                TextInput::make('telefono')
                    ->label('Teléfono')
                    ->tel()
                    ->maxLength(20),
                TextInput::make('horario')
                    ->label('Horario')
                    ->maxLength(100)
                    ->placeholder('Lun-Dom 8:00 - 20:00'),
            ]);
    }
}
