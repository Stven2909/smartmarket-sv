<?php

namespace App\Http\Controllers;

use App\Models\Sucursal;
use Illuminate\Http\Request;

class SucursalController extends Controller
{
    /*
     * GET: /api/sucursales
     * Lista las sucursales con su supermercado, para poblar la vista de ubicacion
     * del frontend. Relacion: Sucursal belongsTo Supermercado (singular).
     */
    public function index(Request $request)
    {
        return Sucursal::with('supermercado')
            ->orderBy('nombre')
            ->get();
    }
}
