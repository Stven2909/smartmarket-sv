<?php

namespace App\Http\Controllers;

use App\Models\PrecioActual;
use Illuminate\Http\Request;

class PromocionController extends Controller
{
    /*
     * GET: /api/promociones
     * Lista los precios con promocion activa (tiene_promocion = true).
     * El frontend deriva ahorro y porcentaje comparando precio_normal vs precio_final.
     * Relaciones: PrecioActual belongsTo producto (belongsTo categoria) y
     * sucursal (belongsTo supermercado).
     */
    public function index(Request $request)
    {
        $query = PrecioActual::where('tiene_promocion', true)
            ->with(['producto.categoria', 'sucursal.supermercado']);

        if ($request->filled('categoria_id')) {
            $query->whereHas('producto', function ($q) use ($request) {
                $q->where('categoria_id', $request->input('categoria_id'));
            });
        }

        return $query->orderBy('producto_id')->paginate(30);
    }
}
