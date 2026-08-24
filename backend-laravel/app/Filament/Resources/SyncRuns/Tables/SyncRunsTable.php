<?php

namespace App\Filament\Resources\SyncRuns\Tables;

use App\Models\SyncRun;
use Filament\Actions\Action;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Filters\SelectFilter;
use Filament\Tables\Table;
use Illuminate\Support\HtmlString;

class SyncRunsTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->defaultSort('iniciada_en', 'desc')
            ->columns([
                TextColumn::make('fuente')
                    ->badge()
                    ->color('gray')
                    ->sortable(),
                TextColumn::make('modo')
                    ->badge()
                    ->color('info'),
                TextColumn::make('estado')
                    ->badge()
                    ->color(fn (string $state): string => match ($state) {
                        'exitosa' => 'success',
                        'fallida' => 'danger',
                        default => 'warning', // en_proceso u otros
                    })
                    ->sortable(),
                TextColumn::make('productos_obtenidos')
                    ->label('Obtenidos')
                    ->numeric()
                    ->alignEnd(),
                TextColumn::make('productos_nuevos')
                    ->label('Nuevos')
                    ->numeric()
                    ->alignEnd(),
                TextColumn::make('productos_duplicados')
                    ->label('Duplicados')
                    ->numeric()
                    ->alignEnd()
                    ->toggleable(),
                TextColumn::make('rechazados')
                    ->label('Rechazados')
                    ->numeric()
                    ->alignEnd()
                    ->toggleable(),
                TextColumn::make('iniciada_en')
                    ->label('Iniciada')
                    ->dateTime()
                    ->sortable(),
                TextColumn::make('finalizada_en')
                    ->label('Finalizada')
                    ->dateTime()
                    ->since()
                    ->toggleable(),
            ])
            ->filters([
                SelectFilter::make('estado')
                    ->options([
                        'exitosa' => 'Exitosa',
                        'fallida' => 'Fallida',
                        'en_proceso' => 'En proceso',
                    ]),
                SelectFilter::make('fuente')
                    ->options(fn (): array => array_combine(
                        array_keys(config('price_providers.fuentes', [])),
                        array_keys(config('price_providers.fuentes', [])),
                    )),
            ])
            ->recordActions([
                self::accionVerDetalle(),
            ]);
    }

    private static function accionVerDetalle(): Action
    {
        return Action::make('verDetalle')
            ->label('Detalle')
            ->icon('heroicon-o-code-bracket')
            ->color('gray')
            ->visible(fn (SyncRun $record): bool => $record->detalle !== null || $record->mensaje_error !== null)
            ->modalHeading(fn (SyncRun $record): string => "Ciclo #{$record->id} — {$record->fuente}")
            ->modalContent(function (SyncRun $record): HtmlString {
                $secciones = [];

                if ($record->mensaje_error !== null) {
                    $secciones[] = '<p><strong>Error:</strong> ' . e($record->mensaje_error) . '</p>';
                }

                $secciones[] = '<pre style="white-space:pre-wrap;max-height:28rem;overflow:auto;font-size:.75rem">'
                    . e(json_encode($record->detalle ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE))
                    . '</pre>';

                return new HtmlString(implode('', $secciones));
            })
            ->modalSubmitAction(false);
    }
}
