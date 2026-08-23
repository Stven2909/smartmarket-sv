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
     *
     * ADR-11: se excluyen las sucursales virtuales "Tienda en línea" (las únicas
     * sin coordenadas): existen solo para anclar internamente los precios
     * automáticos y su supermercado — no son lugares visitables.
     */
    public function index(Request $request)
    {
        return Sucursal::with('supermercado')
            ->whereNotNull('latitud')
            ->orderBy('nombre')
            ->get();
    }
}
