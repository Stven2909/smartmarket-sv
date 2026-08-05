<?php

namespace App\Http\Controllers;

use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Services\Optimization\ComparisonService;
use App\Services\Optimization\OptimizationService;
use Illuminate\Http\Request;

class ListaCompraController extends Controller
{
    public function __construct(
        private ComparisonService $comparisonService,
        private OptimizationService $optimizationService,
    ) {}

    // Chequeo de propiedad: solo el dueño de la lista puede verla o modificarla.
    private function verificarPropietario(ListaCompra $lista): void
    {
        if ($lista->usuario_id !== auth()->id()) {
            abort(403, 'No tienes permiso para acceder a esta lista.');
        }
    }

    // GET /api/listas
    public function index(Request $request)
    {
        return ListaCompra::where('usuario_id', $request->user()->id)
            ->withCount('detalles')
            ->orderByDesc('fecha')
            ->paginate(20);
    }

    // POST /api/listas
    public function store(Request $request)
    {
        $data = $request->validate([
            'nombre' => ['required', 'string', 'max:150'],
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

    // GET /api/listas/{lista}
    public function show(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        return $lista->load('detalles.producto.categoria');
    }

    // DELETE /api/listas/{lista}
    public function destroy(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $lista->delete();

        return response()->json(['message' => 'Lista eliminada.']);
    }

    // POST /api/listas/{lista}/productos
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

    // PATCH /api/listas/{lista}/productos/{detalle}
    public function actualizarProducto(Request $request, ListaCompra $lista, ListaCompraDetalles $detalle)
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

    // DELETE /api/listas/{lista}/productos/{detalle}
    public function quitarProducto(ListaCompra $lista, ListaCompraDetalles $detalle)
    {
        $this->verificarPropietario($lista);

        if ($detalle->lista_id !== $lista->id) {
            abort(404);
        }

        $detalle->delete();

        return response()->json(['message' => 'Producto quitado de la lista.']);
    }

    // GET /api/listas/{lista}/comparar
    // Ahora solo coordina la petición — todo el cálculo vive en ComparisonService
    // (Fase 4, cierre de la deuda técnica de Fase 3 — 02-arquitectura.md sección 3).
    public function comparar(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $comparacion = $this->comparisonService->comparar($lista);

        if (empty($comparacion['resultados'])) {
            return response()->json(['message' => 'La lista no tiene productos todavía, o ninguno tiene precio disponible.'], 422);
        }

        return response()->json($comparacion);
    }

    // GET /api/listas/{lista}/optimizar?lat=13.70&lng=-89.20
    // Fase 4: calcula distancia + Score para cada sucursal, ordena por mejor
    // alternativa (menor Score), y persiste el resultado en ResultadoOptimizacion.
    public function optimizar(Request $request, ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $data = $request->validate([
            'lat' => ['required', 'numeric', 'between:-90,90'],
            'lng' => ['required', 'numeric', 'between:-180,180'],
        ]);

        $comparacionPrevia = $this->comparisonService->comparar($lista);
        if (empty($comparacionPrevia['resultados'])) {
            return response()->json(['message' => 'La lista no tiene productos todavía, o ninguno tiene precio disponible.'], 422);
        }

        $resultado = $this->optimizationService->optimizar($lista, (float) $data['lat'], (float) $data['lng']);

        return response()->json($resultado);
    }
}
