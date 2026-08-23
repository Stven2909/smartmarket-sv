<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Zona de Staging del Flujo 2 (02-arquitectura.md §6): todo lo que recolecta
     * un Price Provider aterriza aquí crudo — jamás escribe directo a
     * precios_actuales ni al Catálogo Maestro (ADR-006).
     *
     * Política de contenido (ADR-10): solo datos fácticos como columnas
     * (nombre, precio, unidad, categoría cruda, URL). Las imágenes y textos
     * promocionales del supermercado NO se promueven; si vienen en la respuesta,
     * quedan únicamente dentro de raw_payload como evidencia de auditoría.
     *
     * sku_externo: sha256 hex de "nombre_normalizado|unidad_normalizada"
     * (clave canónica estilo repo hermano) — deduplica entre corridas sin
     * depender del SKU interno de cada supermercado.
     */
    public function up(): void
    {
        Schema::create('producto_raw', function (Blueprint $table) {
            $table->id();
            // Clave de la fuente en config/price_providers.php (ej. 'vtex-walmart'
            // no: la fuente es la clave 'walmart'; el modo va implícito ahí).
            $table->string('fuente', 50);
            $table->string('sku_externo', 64);

            // Campos fácticos validados (límites del repo hermano: nombre 3–220).
            $table->string('nombre', 220);
            $table->string('unidad', 50)->nullable();
            $table->string('categoria_raw', 150)->nullable();
            $table->decimal('precio_normal', 10, 2)->nullable(); // precio anterior / lista
            $table->decimal('precio_final', 10, 2);
            $table->boolean('tiene_promocion')->default(false);
            $table->boolean('disponible')->nullable();
            $table->text('url_fuente')->nullable();

            // Respuesta original tal cual vino (auditoría completa, TTL/limpieza a definir).
            $table->json('raw_payload');

            // Estados del ERD Nivel 2 (ProductoRaw): pendiente → publicado |
            // error (validación dura) | revision_manual (match ambiguo).
            $table->string('estado', 30)->default('pendiente');
            $table->string('motivo_rechazo', 255)->nullable();

            $table->foreignId('sync_run_id')
                ->nullable()
                ->constrained('sync_runs')
                ->nullOnDelete();
            $table->timestamp('procesado_at')->nullable();

            $table->timestamps();

            $table->unique(['fuente', 'sku_externo']);
            $table->index('estado');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('producto_raw');
    }
};
