<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Health check por corrida de sincronización (06-referencia-extractor-vtex.md
     * §4 punto 5): cada corrida de una fuente registra sus conteos para comparar
     * contra la corrida previa de la misma fuente — caída brusca ⇒ alertar y no
     * publicar esa fuente (§6.4 de 02-arquitectura.md).
     */
    public function up(): void
    {
        Schema::create('sync_runs', function (Blueprint $table) {
            $table->id();
            // Clave de la fuente en config/price_providers.php ('walmart',
            // 'super-selectos', ...).
            $table->string('fuente', 50);
            $table->string('modo', 20); // html | vtex
            // en_curso | exitosa | fallida | abortada
            $table->string('estado', 20)->default('en_curso');
            $table->timestamp('iniciada_en');
            $table->timestamp('finalizada_en')->nullable();

            $table->unsignedInteger('productos_obtenidos')->default(0);
            $table->unsignedInteger('productos_nuevos')->default(0);
            $table->unsignedInteger('productos_duplicados')->default(0);
            $table->unsignedInteger('rechazados')->default(0);

            // Conteos por motivo de rechazo, páginas recorridas, duración, etc.
            $table->json('detalle')->nullable();
            $table->text('mensaje_error')->nullable();

            $table->timestamps();

            $table->index(['fuente', 'created_at']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('sync_runs');
    }
};
