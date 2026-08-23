<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Complemento del ADR-11 (sucursal online): cuando la mejor opción de una
     * optimización sea una Tienda en línea (sin coordenadas), distancia y tiempo
     * no aplican y se persisten como nulos en lugar de fingir valores.
     */
    public function up(): void
    {
        Schema::table('resultados_optimizacion', function (Blueprint $table) {
            $table->decimal('distancia', 10, 2)->nullable()->change();
            $table->integer('tiempo')->nullable()->change(); // minutos
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('resultados_optimizacion', function (Blueprint $table) {
            $table->decimal('distancia', 10, 2)->change();
            $table->integer('tiempo')->change();
        });
    }
};
