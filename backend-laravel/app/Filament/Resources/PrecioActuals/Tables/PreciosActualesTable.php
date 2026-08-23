<?php

namespace App\Filament\Resources\PrecioActuals\Tables;

use Filament\Actions\BulkActionGroup;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Filters\SelectFilter;
use Filament\Tables\Filters\TernaryFilter;
use Filament\Tables\Table;

class PreciosActualesTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->defaultSort('fecha_actualizacion', 'desc')
            ->columns([
                TextColumn::make('producto.nombre')
                    ->label('Producto')
                    ->searchable()
                    ->sortable()
                    ->wrap(),
                TextColumn::make('sucursal.supermercado.nombre')
                    ->label('Supermercado')
                    ->badge()
                    ->sortable(),
                TextColumn::make('sucursal.nombre')
                    ->label('Sucursal')
                    ->toggleable(),
                TextColumn::make('precio_normal')
                    ->label('Normal')
                    ->money('USD')
                    ->sortable()
                    ->toggleable(),
                TextColumn::make('precio_final')
                    ->label('Final')
                    ->money('USD')
                    ->weight('bold')
                    ->color('success')
                    ->sortable(),
                TextColumn::make('tipo_promocion')
                    ->label('Promoción')
                    ->badge()
                    ->placeholder('—'),
                TextColumn::make('origen_dato')
                    ->label('Origen')
                    ->badge()
                    ->color(fn (?string $state): string => str_starts_with((string) $state, 'manual') ? 'info' : 'warning')
                    ->placeholder('—')
                    ->toggleable(),
                TextColumn::make('fecha_actualizacion')
                    ->label('Actualizado')
                    ->dateTime()
                    ->sortable(),
            ])
            ->filters([
                TernaryFilter::make('tiene_promocion')
                    ->label('Con promoción'),
                SelectFilter::make('sucursal')
                    ->label('Sucursal')
                    ->relationship('sucursal', 'nombre')
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
