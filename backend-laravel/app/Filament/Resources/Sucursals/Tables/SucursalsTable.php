<?php

namespace App\Filament\Resources\Sucursals\Tables;

use Filament\Actions\BulkActionGroup;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Tables\Columns\IconColumn;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Filters\SelectFilter;
use Filament\Tables\Table;

class SucursalsTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('supermercado.nombre')
                    ->label('Supermercado')
                    ->sortable(),
                TextColumn::make('nombre')
                    ->label('Sucursal')
                    ->searchable()
                    ->sortable(),
                TextColumn::make('direccion')
                    ->label('Dirección')
                    ->limit(45)
                    ->toggleable(),
                TextColumn::make('telefono')
                    ->label('Teléfono')
                    ->placeholder('—')
                    ->toggleable(),
                IconColumn::make('es_online')
                    ->label('Canal online')
                    ->state(fn ($record): bool => $record->latitud === null)
                    ->boolean()
                    ->trueIcon('heroicon-o-globe-alt')
                    ->falseIcon('heroicon-o-map-pin'),
                TextColumn::make('latitud')
                    ->numeric(decimalPlaces: 6)
                    ->toggleable(isToggledHiddenByDefault: true),
                TextColumn::make('longitud')
                    ->numeric(decimalPlaces: 6)
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                SelectFilter::make('supermercado')
                    ->relationship('supermercado', 'nombre')
                    ->searchable()
                    ->preload(),
            ])
            ->recordActions([
                EditAction::make(),
            ])
            ->toolbarActions([
                BulkActionGroup::make([
                    DeleteBulkAction::make(),
                ]),
            ]);
    }
}
