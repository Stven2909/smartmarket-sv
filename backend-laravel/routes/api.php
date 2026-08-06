<?php

use App\Http\Controllers\Auth\AuthController;
use App\Http\Controllers\CategoriaController;
use App\Http\Controllers\ListaCompraController;
use App\Http\Controllers\ProductoController;
use App\Http\Controllers\PromocionController;
use App\Http\Controllers\SucursalController;
use Illuminate\Support\Facades\Route;

// Rutas públicas de autenticación
Route::post('/register', [AuthController::class, 'register']);
Route::post('/login', [AuthController::class, 'login']);

// Catálogo Maestro (Fase 2) — público, no requiere login para consultarse.
// Importante: la ruta /buscar debe ir ANTES de /{producto}, si no Laravel intenta
// interpretar "buscar" como si fuera un {producto} y nunca llega al método correcto.
Route::get('/productos/buscar', [ProductoController::class, 'buscar']);
Route::get('/productos/{producto}', [ProductoController::class, 'show']);
Route::get('/productos', [ProductoController::class, 'index']);
//nueva
Route::get('/productos/{producto}/historial', [ProductoController::class, 'historial']);
Route::get('/categorias', [CategoriaController::class, 'index']);

// Sucursales y Promociones: se construyeron durante la integración del frontend
// (fuera del orden original de fases). /promociones adelanta trabajo de la Fase 5.
Route::get('/sucursales', [SucursalController::class, 'index']);
Route::get('/promociones', [PromocionController::class, 'index']);

// Rutas protegidas (requieren token de Sanctum en el header Authorization: Bearer {token})
Route::middleware('auth:sanctum')->group(function () {
    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/me', [AuthController::class, 'me']);
    //nuevas
    Route::patch('/listas/{lista}/completar', [ListaCompraController::class, 'completar']);
    Route::get('/listas/{lista}/promociones', [ListaCompraController::class, 'promociones']);

    // Listas de compra y Comparador (Fase 3)
    Route::get('/listas', [ListaCompraController::class, 'index']);
    Route::post('/listas', [ListaCompraController::class, 'store']);
    Route::get('/listas/{lista}', [ListaCompraController::class, 'show']);
    Route::delete('/listas/{lista}', [ListaCompraController::class, 'destroy']);
    Route::get('/listas/{lista}/comparar', [ListaCompraController::class, 'comparar']);
    Route::get('/listas/{lista}/optimizar', [ListaCompraController::class, 'optimizar']);
    Route::post('/listas/{lista}/productos', [ListaCompraController::class, 'agregarProducto']);
    Route::patch('/listas/{lista}/productos/{detalle}', [ListaCompraController::class, 'actualizarProducto']);
    Route::delete('/listas/{lista}/productos/{detalle}', [ListaCompraController::class, 'quitarProducto']);
});
