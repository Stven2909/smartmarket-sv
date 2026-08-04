<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('resultados_optimizacion', function (Blueprint $table) {
            $table->id();
            $table->foreignId('lista_compra_id')->constrained('listas_compra')->cascadeOnDelete();
            $table->decimal('score', 10, 4);
            $table->decimal('ahorro', 10, 2)->default(0);
            $table->decimal('distancia', 10, 2);
            $table->integer('tiempo'); // minutos
            $table->json('supermercados'); // resumen liviano: [{supermercado, sucursal, score}, ...]
            $table->json('resultado_json'); // payload completo, el mismo que consumirá el Sistema Experto
            $table->timestamp('fecha')->useCurrent();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('resultados_optimizacion');
    }
};
