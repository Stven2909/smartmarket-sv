<?php

namespace App\Filament\Resources\PrecioActuals;

use App\Filament\Resources\PrecioActuals\Pages\CreatePrecioActual;
use App\Filament\Resources\PrecioActuals\Pages\EditPrecioActual;
use App\Filament\Resources\PrecioActuals\Pages\ListPrecioActuals;
use App\Filament\Resources\PrecioActuals\Schemas\PrecioActualForm;
use App\Filament\Resources\PrecioActuals\Tables\PreciosActualesTable;
use App\Models\PrecioActual;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;

class PrecioActualResource extends Resource
{
    protected static ?string $model = PrecioActual::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedCurrencyDollar;

    protected static ?string $modelLabel = 'Precio actual';

    protected static ?string $pluralModelLabel = 'Precios actuales';

    protected static ?int $navigationSort = 6;

    public static function form(Schema $schema): Schema
    {
        return PrecioActualForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return PreciosActualesTable::configure($table);
    }

    public static function getRelations(): array
    {
        return [
            //
        ];
    }

    public static function getPages(): array
    {
        return [
            'index' => ListPrecioActuals::route('/'),
            'create' => CreatePrecioActual::route('/create'),
            'edit' => EditPrecioActual::route('/{record}/edit'),
        ];
    }
}
