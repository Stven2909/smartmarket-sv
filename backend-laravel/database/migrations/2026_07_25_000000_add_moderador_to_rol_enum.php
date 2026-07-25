<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    // Laravel implementa enum() en PostgreSQL como una restricción CHECK (no un tipo
    // ENUM nativo), así que para agregar un valor hay que reemplazar esa restricción
    // directamente, no se puede usar change() con Blueprint.
    //
    // Alinea la tabla users con 02-arquitectura.md sección 8.1: "Roles de usuario:
    // Administrador, Moderador, Usuario normal".
    public function up(): void
    {
        DB::statement('ALTER TABLE users DROP CONSTRAINT IF EXISTS users_rol_check');
        DB::statement("ALTER TABLE users ADD CONSTRAINT users_rol_check CHECK (rol IN ('admin', 'moderador', 'usuario'))");
    }

    public function down(): void
    {
        DB::statement('ALTER TABLE users DROP CONSTRAINT IF EXISTS users_rol_check');
        DB::statement("ALTER TABLE users ADD CONSTRAINT users_rol_check CHECK (rol IN ('admin', 'usuario'))");
    }
};
