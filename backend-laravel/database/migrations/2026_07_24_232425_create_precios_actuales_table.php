<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Tabla/Migracion para contener los precios actuales por cada sucursal
     */
    public function up(): void
    {
        Schema::create('precios_actuales', function (Blueprint $table) {
            $table->id();
            $table->foreignId('producto_id')->constrained('productos')->cascadeOnDelete();
            $table->foreignId('sucursal_id')->constrained('sucursales')->cascadeOnDelete();
            $table->decimal('precio_normal', 10, 2);
            $table->decimal('precio_final', 10, 2);
            $table->boolean('tiene_promocion')->default(false);
            $table->string('tipo_promocion', 50)->nullable();
            $table->timestamp('fecha_actualizacion')->useCurrent();
            $table->string('origen_dato', 50)->nullable();
            $table->timestamps();

            // El comparador siempre consultaria esta tabla por producto+sucursal, así que
            // conviene un índice único para evitar duplicados mas adelante.
            $table->unique(['producto_id', 'sucursal_id']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('precios_actuales');
    }
};
