<?php

namespace App\Filament\Resources\Productos\RelationManagers;

use App\Services\NormalizadorTexto;
use Filament\Actions\BulkActionGroup;
use Filament\Actions\CreateAction;
use Filament\Actions\DeleteAction;
use Filament\Actions\DeleteBulkAction;
use Filament\Actions\EditAction;
use Filament\Forms\Components\TextInput;
use Filament\Resources\RelationManagers\RelationManager;
use Filament\Schemas\Schema;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Table;

class AliasRelationManager extends RelationManager
{
    protected static string $relationship = 'alias';

    protected static ?string $title = 'Alias de búsqueda';

    public function form(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('alias')
                    ->label('Alias')
                    ->required()
                    ->maxLength(200)
                    ->columnSpanFull()
                    ->helperText('Se guarda normalizado (sin tildes, minúsculas) igual que el buscador'),
            ]);
    }

    public function table(Table $table): Table
    {
        return $table
            ->recordTitleAttribute('alias')
            ->columns([
                TextColumn::make('alias')
                    ->searchable()
                    ->sortable(),
                TextColumn::make('origen')
                    ->badge()
                    ->color(fn (string $state): string => $state === 'manual' ? 'info' : 'warning'),
                TextColumn::make('created_at')
                    ->dateTime()
                    ->sortable()
                    ->toggleable(isToggledHiddenByDefault: true),
            ])
            ->filters([
                //
            ])
            ->headerActions([
                // Los alias creados desde el panel se normalizan con el mismo
                // criterio del Motor de Normalizacion, para que el buscador los
                // matchee identico a los que publica el extractor.
                CreateAction::make()
                    ->mutateFormDataUsing(fn (array $data): array => [
                        'alias' => NormalizadorTexto::limpiar($data['alias'] ?? ''),
                        'origen' => 'manual',
                    ]),
            ])
            ->recordActions([
                EditAction::make()
                    ->mutateFormDataUsing(fn (array $data): array => [
                        ...$data,
                        'alias' => NormalizadorTexto::limpiar($data['alias'] ?? ''),
                    ]),
                DeleteAction::make(),
            ])
            ->toolbarActions([
                BulkActionGroup::make([
                    DeleteBulkAction::make(),
                ]),
            ]);
    }
}
