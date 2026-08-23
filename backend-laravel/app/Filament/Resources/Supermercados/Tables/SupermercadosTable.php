<?php

namespace App\Filament\Resources\Supermercados\Tables;

use Filament\Actions\BulkActionGroup;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Tables\Columns\IconColumn;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class SupermercadosTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->columns([
                TextColumn::make('nombre')
                    ->label('Supermercado')
                    ->searchable()
                    ->sortable(),
                TextColumn::make('sucursales_count')
                    ->counts('sucursales')
                    ->label('Sucursales')
                    ->sortable(),
                TextColumn::make('sitio_web')
                    ->label('Sitio web')
                    ->url(fn (?string $state): ?string => $state)
                    ->toggleable(),
                IconColumn::make('activo')
                    ->boolean()
                    ->sortable(),
                TextColumn::make('created_at')
                    ->label('Creado')
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),
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
