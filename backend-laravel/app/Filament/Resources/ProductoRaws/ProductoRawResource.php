<?php

namespace App\Filament\Resources\ProductoRaws;

use App\Filament\Resources\ProductoRaws\Pages\ListProductoRaws;
use App\Filament\Resources\ProductoRaws\Tables\ProductoRawsTable;
use App\Models\ProductoRaw;
use BackedEnum;
use Filament\Resources\Resource;
use Filament\Support\Icons\Heroicon;
use Filament\Tables\Table;
use UnitEnum;

// Zona de curacion del Flujo 2: lo que trae el extractor se inspecciona y se
// publica/rechaza desde aca, SIEMPRE via StagingProcessor — este recurso no
// crea ni edita registros (el staging solo escribe desde precios:sync).
class ProductoRawResource extends Resource
{
    protected static ?string $model = ProductoRaw::class;

    protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedInboxArrowDown;

    protected static ?string $modelLabel = 'Registro de staging';

    protected static ?string $pluralModelLabel = 'Staging del extractor';

    protected static string|UnitEnum|null $navigationGroup = 'Extractor';

    protected static ?int $navigationSort = 7;

    public static function table(Table $table): Table
    {
        return ProductoRawsTable::configure($table);
    }

    public static function getPages(): array
    {
        return [
            'index' => ListProductoRaws::route('/'),
        ];
    }
}
