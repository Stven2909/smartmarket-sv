<?php

namespace App\Filament\Resources\Sucursals;

use App\Filament\Resources\Sucursals\Pages\CreateSucursal;
use App\Filament\Resources\Sucursals\Pages\EditSucursal;
use App\Filament\Resources\Sucursals\Pages\ListSucursals;
use App\Filament\Resources\Sucursals\Schemas\SucursalForm;
use App\Filament\Resources\Sucursals\Tables\SucursalsTable;
use App\Models\Sucursal;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;
use UnitEnum;

class SucursalResource extends Resource
{
    protected static ?string $model = Sucursal::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedMapPin;

    protected static ?string $modelLabel = 'Sucursal';

    protected static ?string $pluralModelLabel = 'Sucursales';

    protected static string|UnitEnum|null $navigationGroup = 'Red de tiendas';

    protected static ?int $navigationSort = 4;

    public static function form(Schema $schema): Schema
    {
        return SucursalForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return SucursalsTable::configure($table);
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
            'index' => ListSucursals::route('/'),
            'create' => CreateSucursal::route('/create'),
            'edit' => EditSucursal::route('/{record}/edit'),
        ];
    }
}
