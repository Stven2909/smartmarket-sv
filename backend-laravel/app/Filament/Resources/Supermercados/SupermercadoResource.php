<?php

namespace App\Filament\Resources\Supermercados;

use App\Filament\Resources\Supermercados\Pages\CreateSupermercado;
use App\Filament\Resources\Supermercados\Pages\EditSupermercado;
use App\Filament\Resources\Supermercados\Pages\ListSupermercados;
use App\Filament\Resources\Supermercados\Schemas\SupermercadoForm;
use App\Filament\Resources\Supermercados\Tables\SupermercadosTable;
use App\Models\Supermercado;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Schemas\Schema;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;

class SupermercadoResource extends Resource
{
    protected static ?string $model = Supermercado::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedBuildingStorefront;

    protected static ?string $modelLabel = 'Supermercado';

    protected static ?string $pluralModelLabel = 'Supermercados';

    protected static ?int $navigationSort = 2;

    public static function form(Schema $schema): Schema
    {
        return SupermercadoForm::configure($schema);
    }

    public static function table(Table $table): Table
    {
        return SupermercadosTable::configure($table);
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
            'index' => ListSupermercados::route('/'),
            'create' => CreateSupermercado::route('/create'),
            'edit' => EditSupermercado::route('/{record}/edit'),
        ];
    }
}
