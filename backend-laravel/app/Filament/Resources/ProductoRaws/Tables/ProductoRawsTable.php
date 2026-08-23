<?php

namespace App\Filament\Resources\ProductoRaws\Tables;

use App\Models\ProductoRaw;
use App\Services\PriceProviders\StagingProcessor;
use Filament\Actions\Action;
use Filament\Actions\BulkAction;
use Filament\Actions\BulkActionGroup;
use Filament\Forms\Components\TextInput;
use Filament\Notifications\Notification;
use Filament\Tables\Columns\IconColumn;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Filters\SelectFilter;
use Filament\Tables\Filters\TernaryFilter;
use Filament\Tables\Table;
use Illuminate\Support\Collection;
use Illuminate\Support\HtmlString;

class ProductoRawsTable
{
    public static function configure(Table $table): Table
    {
        return $table
            ->defaultSort('id', 'desc')
            ->columns([
                TextColumn::make('fuente')
                    ->badge()
                    ->color('gray')
                    ->sortable(),
                TextColumn::make('nombre')
                    ->label('Nombre crudo')
                    ->searchable()
                    ->wrap(),
                TextColumn::make('unidad')
                    ->label('Unidad')
                    ->placeholder('—')
                    ->toggleable(),
                TextColumn::make('precio_normal')
                    ->label('Normal')
                    ->money('USD')
                    ->placeholder('—')
                    ->toggleable(),
                TextColumn::make('precio_final')
                    ->label('Final')
                    ->money('USD'),
                IconColumn::make('tiene_promocion')
                    ->boolean()
                    ->label('Promo'),
                IconColumn::make('disponible')
                    ->boolean()
                    ->label('Disp.')
                    ->toggleable(),
                TextColumn::make('estado')
                    ->badge()
                    ->color(fn (string $state): string => match ($state) {
                        'publicado' => 'success',
                        'pendiente' => 'warning',
                        default => 'danger', // rechazado | error
                    })
                    ->sortable(),
                TextColumn::make('motivo_rechazo')
                    ->label('Motivo')
                    ->limit(30)
                    ->tooltip(fn (?string $state): ?string => $state)
                    ->placeholder('—')
                    ->toggleable(),
                TextColumn::make('url_fuente')
                    ->label('URL')
                    ->url(fn (?string $state): ?string => $state, shouldOpenInNewTab: true)
                    ->limit(20)
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                SelectFilter::make('estado')
                    ->options([
                        'pendiente' => 'Pendiente',
                        'publicado' => 'Publicado',
                        'rechazado' => 'Rechazado',
                        'error' => 'Error',
                    ]),
                SelectFilter::make('fuente')
                    ->options(fn (): array => array_combine(
                        array_keys(config('price_providers.fuentes', [])),
                        array_keys(config('price_providers.fuentes', [])),
                    )),
                TernaryFilter::make('disponible'),
            ])
            ->recordActions([
                self::accionPublicar(),
                self::accionRechazar(),
                self::accionVerPayload(),
            ])
            ->toolbarActions([
                BulkAction::make('publicarSeleccionados')
                    ->label('Publicar seleccionados')
                    ->icon('heroicon-o-cloud-arrow-up')
                    ->color('success')
                    ->requiresConfirmation()
                    ->modalDescription('Publica cada fila pendiente vía StagingProcessor: matching contra catálogo, alias y upsert de precio.')
                    ->action(fn (Collection $records) => self::publicar($records)),

                // El staging no se borra desde el panel: es evidencia de auditoría (ADR-10).
            ]);
    }

    private static function publicar(Collection $filas): void
    {
        $conteos = app(StagingProcessor::class)->procesarFilas($filas);

        Notification::make()
            ->title("Publicados {$conteos['publicados']} de {$conteos['procesados']}")
            ->body("Nuevos productos: {$conteos['nuevos_productos']} · Alias nuevos: {$conteos['alias_nuevos']} · Errores: {$conteos['errores']}")
            ->success($conteos['errores'] === 0)
            ->warning($conteos['errores'] > 0)
            ->send();
    }

    private static function accionPublicar(): Action
    {
        return Action::make('publicar')
            ->label('Publicar')
            ->icon('heroicon-o-cloud-arrow-up')
            ->color('success')
            ->visible(fn (ProductoRaw $record): bool => $record->estado === 'pendiente')
            ->requiresConfirmation()
            ->modalDescription('Publica esta fila vía StagingProcessor: matching contra catálogo, alias y upsert de precio.')
            ->action(fn (ProductoRaw $record) => self::publicar(collect([$record])));
    }

    private static function accionRechazar(): Action
    {
        return Action::make('rechazar')
            ->label('Rechazar')
            ->icon('heroicon-o-x-circle')
            ->color('danger')
            ->visible(fn (ProductoRaw $record): bool => $record->estado === 'pendiente')
            ->requiresConfirmation()
            ->form([
                TextInput::make('motivo')
                    ->label('Motivo del rechazo')
                    ->required()
                    ->maxLength(255),
            ])
            ->action(function (ProductoRaw $record, array $data): void {
                $record->update([
                    'estado' => 'rechazado',
                    'motivo_rechazo' => $data['motivo'],
                    'procesado_at' => now(),
                ]);

                Notification::make()
                    ->title('Registro rechazado')
                    ->body($data['motivo'])
                    ->warning()
                    ->send();
            });
    }

    private static function accionVerPayload(): Action
    {
        return Action::make('verPayload')
            ->label('Payload')
            ->icon('heroicon-o-code-bracket')
            ->color('gray')
            ->modalHeading(fn (ProductoRaw $record): string => "raw_payload — {$record->fuente}")
            ->modalContent(fn (ProductoRaw $record): HtmlString => new HtmlString(
                '<pre style="white-space:pre-wrap;max-height:28rem;overflow:auto;font-size:.75rem">'
                . e(json_encode($record->raw_payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE))
                . '</pre>'
            ))
            ->modalSubmitAction(false);
    }
}
