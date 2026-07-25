<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Esta migracion extiende de la tabla users por defecto, solo se le agrego los campos de Rol y Estado
     */
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->enum('rol', ['admin', 'usuario'])->default('usuario')->after('password');
            $table->enum('estado', ['activo', 'inactivo'])->default('activo')->after('rol');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn(['rol','estado']);
        });
    }
};
