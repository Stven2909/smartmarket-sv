<?php

namespace App\Filament\Resources\PrecioActuals\Schemas;

use Closure;
use App\Models\PrecioActual;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Components\Utilities\Get;
use Filament\Schemas\Schema;

class PrecioActualForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                Select::make('producto_id')
                    ->label('Producto')
                    ->relationship('producto', 'nombre')
                    ->searchable()
                    ->preload()
                    ->required()
                    ->columnSpanFull()
                    ->rules([
                        // Refleja el indice unico (producto_id, sucursal_id):
                        // el comparador consulta siempre por ese par.
                        fn (Get $get, ?PrecioActual $record): Closure => function (string $attribute, $value, Closure $fail) use ($get, $record): void {
                            if (blank($value) || blank($get('sucursal_id'))) {
                                return;
                            }

                            $existe = PrecioActual::where('producto_id', $value)
                                ->where('sucursal_id', $get('sucursal_id'))
                                ->when($record, fn ($q) => $q->where('id', '!=', $record->id))
                                ->exists();

                            if ($existe) {
                                $fail('Ya existe un precio para este producto en esa sucursal. Edítalo en lugar de crear otro.');
                            }
                        },
                    ]),
                Select::make('sucursal_id')
                    ->label('Sucursal')
                    ->relationship('sucursal', 'nombre')
                    ->getOptionLabelFromRecordUsing(fn ($record): string => "{$record->nombre} — {$record->supermercado->nombre}")
                    ->searchable()
                    ->preload()
                    ->required(),
                TextInput::make('precio_normal')
                    ->label('Precio normal')
                    ->numeric()
                    ->minValue(0)
                    ->prefix('$')
                    ->required(),
                TextInput::make('precio_final')
                    ->label('Precio final')
                    ->numeric()
                    ->minValue(0)
                    ->prefix('$')
                    ->required()
                    ->helperText('Lo que paga el cliente hoy'),
                Toggle::make('tiene_promocion')
                    ->label('Tiene promoción')
                    ->live()
                    ->default(false),
                TextInput::make('tipo_promocion')
                    ->label('Tipo de promoción')
                    ->maxLength(50)
                    ->visible(fn (Get $get): bool => (bool) $get('tiene_promocion'))
                    ->placeholder('rebaja, 2x1, membresia...'),
            ]);
    }
}
