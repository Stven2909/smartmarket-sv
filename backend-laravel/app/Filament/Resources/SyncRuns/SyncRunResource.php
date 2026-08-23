<?php

namespace App\Filament\Resources\SyncRuns;

use App\Filament\Resources\SyncRuns\Pages\ListSyncRuns;
use App\Filament\Resources\SyncRuns\Tables\SyncRunsTable;
use App\Models\SyncRun;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;

// Health Monitor visible: cada corrida de precios:sync registra sus conteos
// aqui para compararlas contra la corrida previa de la misma fuente. Solo lectura.
class SyncRunResource extends Resource
{
    protected static ?string $model = SyncRun::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedArrowPathRoundedSquare;

    protected static ?string $modelLabel = 'Corrida de sync';

    protected static ?string $pluralModelLabel = 'Corridas de sincronización';

    protected static ?int $navigationSort = 8;

    public static function table(Table $table): Table
    {
        return SyncRunsTable::configure($table);
    }

    public static function getPages(): array
    {
        return [
            'index' => ListSyncRuns::route('/'),
        ];
    }
}
