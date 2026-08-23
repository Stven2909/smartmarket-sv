<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * ADR-11: la Sucursal "Tienda en línea" es un canal nacional sin ubicación
     * física única. Sus coordenadas quedan nulas y se excluye del ranking por
     * distancia física (Haversine), pero sigue siendo totalmente válida como
     * fuente para la comparación de precios a nivel nacional.
     * Ver docs/08-decision-sucursal-tienda-online.md.
     *
     * Nota para down(): revertir fallará si ya existen sucursales con
     * coordenadas nulas — primero hay que eliminarlas o asignarles ubicación.
     */
    public function up(): void
    {
        Schema::table('sucursales', function (Blueprint $table) {
            $table->decimal('latitud', 9, 6)->nullable()->change();
            $table->decimal('longitud', 9, 6)->nullable()->change();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('sucursales', function (Blueprint $table) {
            $table->decimal('latitud', 9, 6)->change();
            $table->decimal('longitud', 9, 6)->change();
        });
    }
};
