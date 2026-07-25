<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Migracion hecha solo para habilitar la extension 'unaccent' que trae el PostgreSQL, para
     * poder comparar texto e ignorar las tildes, que 'Café' sea igual que 'Cafe'
     * parte del motor de normalizacion previamente establecido en el plan del proyecto
     */
    public function up(): void
    {
        DB::statement('CREATE EXTENSION IF NOT EXISTS unaccent');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        DB::statement('DROP EXTENSION IF EXISTS unaccent');
    }
};
