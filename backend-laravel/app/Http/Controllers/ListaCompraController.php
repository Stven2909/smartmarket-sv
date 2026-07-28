<?php

namespace App\Http\Controllers;

use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\PrecioActual;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;

class ListaCompraController extends Controller
{
    //Checking de propiedad: Solo el dueño de la lista puede verla o modificarla
    //Aqui aplicamos el requisito llamado "Permisos por Recurso"

    private function verificarPropietario(ListaCompra $listaCompra): void
    {
        if ($listaCompra->usuario_id != auth()->id()) {
            abort(403, 'No tienes permiso para acceder a este lista.');
        }
    }

    /*
     * GET: /api/listas - solo las listas del usuario autenticado, las listas ajenas no
     */
    public function index(Request $request)
    {
        return ListaCompra::where('usuario_id', $request->user()->id)
            ->withCount('detalles')
            ->orderByDesc('fecha')
            ->paginate(20);
    }

    /*
     * POST: /api/listas
     * con un json body: { "nombre": "...", "presupuesto": 100, "productos": [{"producto_id":1,"cantidad":2,"esencial":true}, ...] }
     * El array que se creara puede ser opcional, se podra crear una lista vacia para luego ponerle los productos
     */
    public function store(Request $request)
    {
        //Aqui generamos el payload
        $data = $request->validate([
            'nombre' => ['required', 'max:150'],
            'presupuesto' => ['nullable', 'numeric', 'min:0'],
            'productos' => ['nullable', 'array'],
            'productos.*.producto_id' => ['required_with:productos', 'integer', 'exists:productos,id'],
            'productos.*.cantidad' => ['nullable', 'integer', 'min:1'],
            'productos.*.esencial' => ['nullable', 'boolean'],
        ]);

        $lista = ListaCompra::create([
            'usuario_id' => $request->user()->id,
            'nombre' => $data['nombre'],
            'presupuesto' => $data['presupuesto'] ?? null,
            'fecha' => now(),
        ]);

        foreach ($data['productos'] ?? [] as $item) {
            $lista->detalles()->create([
                'producto_id' => $item['producto_id'],
                'cantidad' => $item['cantidad'] ?? 1,
                'esencial' => $item['esencial'] ?? true,
            ]);
        }

        return $lista->load('detalles.producto');
    }

    /*
     * GET: /api/listas/{lista}
     */
    public function show(ListaCompra $listaCompra)
    {
        $this->verificarPropietario($listaCompra);

        return $listaCompra->load('detalles.producto.categoria');
    }

    /*
     * DELETE: /api/listas/{lista}
     * Para borrar una lista
     */
    public function destroy(ListaCompra $listaCompra)
    {
        $this->verificarPropietario($listaCompra);

        $listaCompra->delete();

        return response()->json(['message' => 'Lista eliminada.']);
    }

    /*
     * POST: /api/listas/{lista}/productos
     * Con un body JSON: { "producto_id": 1, "cantidad": 2, "esencial": true }
     */
    public function agregarProducto(Request $request, ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $data = $request->validate([
            'producto_id' => ['required', 'integer', 'exists:productos,id'],
            'cantidad' => ['nullable', 'integer', 'min:1'],
            'esencial' => ['nullable', 'boolean'],
        ]);

        $detalle = $lista->detalles()->create([
            'producto_id' => $data['producto_id'],
            'cantidad' => $data['cantidad'] ?? 1,
            'esencial' => $data['esencial'] ?? true,
        ]);

        return $detalle->load('producto');
    }

    /*
     * PATCH: /api/listas/{lista}/productos/{detalle}
     * Actualizara un producto
     */
    public function actualizarProducto(Request $request, ListaCompra $lista, ListaCompraDetalle $detalle)
    {
        $this->verificarPropietario($lista);

        if ($detalle->lista_id !== $lista->id) {
            abort(404);
        }

        $data = $request->validate([
            'cantidad' => ['nullable', 'integer', 'min:1'],
            'esencial' => ['nullable', 'boolean'],
        ]);

        $detalle->update($data);

        return $detalle->load('producto');
    }

    /*
     * DELETE: /api/listas/{lista}/productos/{detalle}
     *
     */
    public function quitarProducto(ListaCompra $lista, ListaCompraDetalle $detalle)
    {
        $this->verificarPropietario($lista);

        if ($detalle->lista_id !== $lista->id) {
            abort(404);
        }

        $detalle->delete();

        return response()->json(['message' => 'Producto quitado de la lista.']);
    }

    /*
     * GET: /api/listas/{lista}/comparar
     *  El Comparador: calcula el costo total de la lista en cada sucursal donde haya
     *  precios disponibles, y cuántos productos esenciales/opcionales encontró ahí.
     *  Usa los mismos nombres de campo que el contrato JSON del Sistema Experto
     *  (04-sistema-experto.md) para no tener que traducir nada cuando llegue esa fase.
     */
    public function comparar(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $detalles = $lista->detalles()->with('producto')->get();

        if ($detalles->isEmpty()) {
            return response()->json(['message' => 'La lista no tiene productos todavía.'], 422);
        }

        $productoIds = $detalles->pluck('producto_id');
        $totalEsenciales = $detalles->where('esencial', true)->count();
        $totalOpcionales = $detalles->where('esencial', false)->count();

        $preciosPorSucursal = PrecioActual::with('sucursal.supermercado')
            ->whereIn('producto_id', $productoIds)
            ->get()
            ->groupBy('sucursal_id');

        $resultados = [];

        foreach ($preciosPorSucursal as $sucursalId => $preciosSucursal) {
            $costoTotal = 0;
            $esencialesDisponibles = 0;
            $opcionalesDisponibles = 0;

            foreach ($detalles as $detalle) {
                $precio = $preciosSucursal->firstWhere('producto_id', $detalle->producto_id);

                if ($precio) {
                    $costoTotal += $precio->precio_final * $detalle->cantidad;

                    if ($detalle->esencial) {
                        $esencialesDisponibles++;
                    } else {
                        $opcionalesDisponibles++;
                    }
                }
            }

            $sucursal = $preciosSucursal->first()->sucursal;

            $resultados[] = [
                'sucursal_id' => $sucursalId,
                'sucursal' => $sucursal->nombre,
                'supermercado' => $sucursal->supermercado->nombre,
                'costo_total' => round($costoTotal, 2),
                'productos_esenciales_disponibles' => $esencialesDisponibles,
                'productos_esenciales_totales' => $totalEsenciales,
                'productos_opcionales_disponibles' => $opcionalesDisponibles,
                'productos_opcionales_totales' => $totalOpcionales,
                'todos_los_esenciales_disponibles' => $esencialesDisponibles === $totalEsenciales,
                'dentro_del_presupuesto' => $lista->presupuesto === null
                    ? null
                    : $costoTotal <= $lista->presupuesto,
            ];
        }

        // Orden por costo total ascendente — el más barato primero.
        usort($resultados, fn($a, $b) => $a['costo_total'] <=> $b['costo_total']);

        return response()->json([
            'lista' => $lista->nombre,
            'presupuesto' => $lista->presupuesto,
            'resultados' => array_values($resultados),
        ]);
    }
}
