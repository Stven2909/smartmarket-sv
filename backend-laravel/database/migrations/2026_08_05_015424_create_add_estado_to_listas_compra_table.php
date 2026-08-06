<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Migracion para agregar el campo 'Estado' que ayudaria a distinguir
     * una lista activa de una ya completada. Ayuda a Historial de Compras, tambien
     */
    public function up(): void
    {
        Schema::table('listas_compra', function (Blueprint $table) {
            $table->enum('estado', ['activa', 'completada'])->default('activa')->after('presupuesto');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('listas_compra', function (Blueprint $table) {
            $table->dropColumn('estado');
        });
    }
};
