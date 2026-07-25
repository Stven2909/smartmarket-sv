<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Los detalles de cada una de las listas se guardan en una tabla diferente
     */
    public function up(): void
    {
        Schema::create('lista_compra_detalles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('lista_id')->constrained('listas_compra')->cascadeOnDelete();
            $table->foreignId('producto_id')->constrained('productos')->cascadeOnDelete();
            $table->integer('cantidad')->default(1);
            $table->boolean('esencial')->default(true);
            $table->boolean('permite_sustituto')->default(false);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('listas_compra_detalles');
    }
};
