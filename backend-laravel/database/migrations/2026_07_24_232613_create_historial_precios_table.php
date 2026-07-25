<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Tabla para manejar el historial de los precios de cada producto, con su sucursal, supermercado, etc
     */
    public function up(): void
    {
        Schema::create('historial_precios', function (Blueprint $table) {
            $table->id();
            $table->foreignId('producto_id')->constrained('productos')->cascadeOnDelete();
            $table->foreignId('sucursal_id')->constrained('sucursales')->cascadeOnDelete();
            $table->decimal('precio_normal', 10, 2);
            $table->decimal('precio_final', 10, 2);
            $table->string('tipo_promocion', 50)->nullable();
            $table->timestamp('fecha');
            $table->string('origen', 50)->nullable();
            // Sin updated_at a propósito: esta tabla es append-only (ADR-006/007),
            // nunca se actualiza un registro existente, solo se insertan nuevos.
            $table->timestamp('created_at')->useCurrent();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('historial_precios');
    }
};
