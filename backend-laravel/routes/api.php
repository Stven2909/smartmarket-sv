<?php

use App\Http\Controllers\Auth\AuthController;
use App\Http\Controllers\CategoriaController;
use App\Http\Controllers\ProductoController;
use App\Http\Controllers\ListaCompraController;
use Illuminate\Support\Facades\Route;

// Rutas públicas de autenticacion
Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);

//Catalogo Maestro - publico, no requiere login-cuenta para consultarlo
Route::get('/productos/buscar', [ProductoController::class, 'buscar']);
Route::get('/productos/{producto}', [ProductoController::class, 'show']);
Route::get('/productos', [ProductoController::class, 'index']);
Route::get('/categorias', [CategoriaController::class, 'index']);

// Rutas protegidas (requieren token de Sanctum en el header Authorization: Bearer {token})
Route::middleware('auth:sanctum')->group(function () {
    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/me', [AuthController::class, 'me']);

    // Aquí se irán agregando el resto de endpoints de la Fase 2 en adelante
    // (catálogo, listas de compra, comparador, etc.)

    //Listas de compra y Comparador (Fase 3)
    Route::get('/listas', [ListaCompraController::class, 'index']);
    Route::post('/listas', [ListaCompraController::class, 'store']);
    Route::get('/listas/{lista}', [ListaCompraController::class, 'show']);
    Route::delete('/listas/{lista}', [ListaCompraController::class, 'destroy']);
    Route::get('/listas/{lista}/comparar', [ListaCompraController::class, 'comparar']);
    Route::post('/listas/{lista}/productos', [ListaCompraController::class, 'agregarProducto']);
    Route::patch('/listas/{lista}/productos/{detalle}', [ListaCompraController::class, 'actualizarProducto']);
    Route::delete('/listas/{lista}/productos/{detalle}', [ListaCompraController::class, 'quitarProducto']);

});
