<?php

namespace App\Filament\Resources\Users\Schemas;

use Filament\Forms\Components\Select;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class UserForm
{
    public static function configure(Schema $schema): Schema
    {
        return $schema
            ->components([
                TextInput::make('name')
                    ->label('Nombre')
                    ->required()
                    ->maxLength(255),
                TextInput::make('email')
                    ->label('Correo electrónico')
                    ->email()
                    ->required()
                    ->unique(ignoreRecord: true)
                    ->maxLength(255),
                TextInput::make('password')
                    ->label('Contraseña')
                    ->password()
                    ->revealable()
                    ->required(fn (string $operation): bool => $operation === 'create')
                    ->dehydrated(fn (?string $state): bool => filled($state))
                    ->minLength(8)
                    ->hint('En edición: dejar vacío para conservar la actual'),
                Select::make('rol')
                    ->options([
                        'admin' => 'Administrador',
                        // La BD ya permite 'moderador' (CHECK users_rol_check,
                        // migración 2026_07_25) aunque aún sin permisos propios.
                        'moderador' => 'Moderador',
                        'usuario' => 'Usuario',
                    ])
                    ->default('usuario')
                    ->required(),
                Select::make('estado')
                    ->options([
                        'activo' => 'Activo',
                        'inactivo' => 'Inactivo',
                    ])
                    ->default('activo')
                    ->required()
                    ->helperText('Inactivo corta el acceso al panel sin borrar la cuenta'),
            ]);
    }
}
