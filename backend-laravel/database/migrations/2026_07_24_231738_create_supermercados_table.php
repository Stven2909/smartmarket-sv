<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Tabla/Migracion para los supermercados
     */
    public function up(): void
    {
        Schema::create('supermercados', function (Blueprint $table) {
            $table->id();
            $table->string('nombre', 100);
            $table->string('logo', 255)->nullable();
            $table->string('sitio_web', 255)-> nullable();
            $table->boolean('activo')->default(true);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('supermercados');
    }
};
