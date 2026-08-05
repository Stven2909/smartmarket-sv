<?php

namespace App\Http\Controllers;

use App\Models\Producto;
use App\Services\NormalizadorTexto;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ProductoController extends Controller
{
    /*
     * GET: /api/productos
     * Lista el catalogo maestro, con un filtro opcional por categorias y paginacion
     */
    public function index (Request $request)
    {
        $query = Producto::with('categoria')->where('activo', true);

        if ($request->filled('categoria_id')){
            $query ->where('categoria_id', $request->input('categoria_id'));
        }

        return $query->orderBy('nombre')->paginate(20);
    }

    /*
     * GET: /api/productos/{producto}
     * Muestra el detalle de un producto especifico con sus precios actuales en cada sucursal
     */
    public function show(Producto $producto)
    {
        return $producto->load(['categoria', 'alias', 'preciosActuales.sucursal.supermercado']);
    }

    /*
     * GET: /api/productos/buscar?q=coca cola
     * Buscador Universal de Productos: compara el termino de busqueda contra nombre, marca y alias
     * usando el mismo criterio de normalizacion simple (sin tildes, minusculas, etc) que ya definimos
     * en el Motor de Normalizacion para el MVP
     * 1- Multi-Palabras: cada palabra o termino debe aparecer en algun lado, sin importar el orden en el
     * que el usuario escriba el nombre del producto
     * 2- Relevancia: coincidencia exacta del primer nombre, luego se ejecuta un 'empieza con', luego pasa a un
     * 'contiene esta palabra en cualquier parte'
     */
    public function buscar(Request $request)
    {
        $request->validate([
            'q' => ['required', 'string', 'min:2', 'max:100'],
        ]);

        $termino = NormalizadorTexto::limpiar($request->input('q'));
        $palabras = array_values(array_filter(explode(' ', $termino)));

        if (empty($palabras)) {
            return Producto::query()->whereRaw('1 = 0')->paginate(20);
        }

        // --- 1. Coincidencias directas en nombre/marca: cada palabra debe aparecer
        //         en el nombre o en la marca (no necesariamente la misma palabra en el mismo
        //         campo que las otras).
        $queryDirecta = Producto::query()->where('activo', true);
        foreach ($palabras as $palabra) {
            $like = '%' . $palabra . '%';
            $queryDirecta->where(function ($q) use ($like) {
                $q->whereRaw('unaccent(lower(nombre)) LIKE unaccent(?)', [$like])
                    ->orWhereRaw('unaccent(lower(marca)) LIKE unaccent(?)', [$like]);
            });
        }
        $idsDirectos = $queryDirecta->pluck('id');

        // --- 2. Coincidencias por alias: todas las palabras deben aparecer juntas
        //         DENTRO DE UN MISMO alias (un alias es un nombre completo alternativo,
        //         ej. "Leche Foremost 1L").
        $queryAlias = DB::table('alias_productos');
        foreach ($palabras as $palabra) {
            $like = '%' . $palabra . '%';
            $queryAlias->whereRaw('unaccent(lower(alias)) LIKE unaccent(?)', [$like]);
        }
        $idsPorAlias = $queryAlias->pluck('producto_id');

        $idsFinales = $idsDirectos->merge($idsPorAlias)->unique()->values();

        if ($idsFinales->isEmpty()) {
            return Producto::query()->whereRaw('1 = 0')->paginate(20);
        }

        // --- 3. Relevancia: se calcula sobre el término completo (sin dividir en
        //         palabras) para distinguir coincidencia exacta / al inicio / en medio / o al final
        $terminoCompleto = $termino;
        $empiezaCon = $termino . '%';
        $contiene = '%' . $termino . '%';

        return Producto::with(['categoria', 'preciosActuales.sucursal.supermercado'])
            ->whereIn('id', $idsFinales)
            ->where('activo', true)
            ->selectRaw(
                "productos.*,
                 CASE
                    WHEN unaccent(lower(nombre)) = unaccent(?) THEN 0
                    WHEN unaccent(lower(nombre)) LIKE unaccent(?) THEN 1
                    WHEN unaccent(lower(marca)) LIKE unaccent(?) THEN 2
                    ELSE 3
                 END AS relevancia",
                [$terminoCompleto, $empiezaCon, $empiezaCon]
            )
            ->orderBy('relevancia')
            ->orderBy('nombre')
            ->paginate(20);
    }
}
