<?php

namespace App\Http\Controllers;

use App\Models\ListaCompra;
use App\Models\ListaCompraDetalles;
use App\Models\ResultadoOptimizacion;
use App\Services\ChatIntentNormalizer;
use App\Services\ExpertSystemService;
use App\Services\Optimization\ComparisonService;
use App\Services\Optimization\OptimizationService;
use Illuminate\Http\Request;

class ListaCompraController extends Controller
{
    public function __construct(
        private ComparisonService $comparisonService,
        private OptimizationService $optimizationService,
        private ExpertSystemService $expertSystemService,
        private ChatIntentNormalizer $chatIntentNormalizer,
    ) {}

    // Chequeo de propiedad: solo el dueño de la lista puede verla o modificarla.
    private function verificarPropietario(ListaCompra $lista): void
    {
        if ($lista->usuario_id !== auth()->id()) {
            abort(403, 'No tienes permiso para acceder a esta lista.');
        }
    }

    // GET /api/listas?estado=completada (el filtro es opcional)
    public function index(Request $request)
    {
        $query = ListaCompra::where('usuario_id', $request->user()->id)
            ->withCount('detalles');

        if ($request->filled('estado')) {
            $query->where('estado', $request->input('estado'));
        }

        return $query->orderByDesc('fecha')->paginate(20);
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
            'estado' => 'activa',
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

        // El OptimizationService ya ejecuta ComparisonService una sola vez.
        // Antes se comparaba aquí para validar y otra vez dentro del servicio:
        // el mismo trabajo se hacía dos veces por cada optimización.
        $resultado = $this->optimizationService->optimizar($lista, (float) $data['lat'], (float) $data['lng']);

        if (empty($resultado['resultados'])) {
            return response()->json(['message' => 'La lista no tiene productos todavía, o ninguno tiene precio disponible.'], 422);
        }

        return response()->json($resultado);
    }

    // POST /api/listas/{lista}/chat
    // Asistente explicativo del Sistema Experto. No conserva estado: el frontend
    // repite facts + recomendación de la corrida ya guardada para que el experto
    // pueda explicarla con el mismo contexto que generó la recomendación.
    // Primero se verifica que esa corrida exista y pertenezca a ESTA lista; si la
    // alternativa no tuvo recomendación, o el asistente no responde, se devuelve
    // HTTP 200 con fallback NO_DISPONIBLE (la recomendación principal sigue viva).
    public function chat(Request $request, ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $data = $request->validate([
            'message' => ['required', 'string', 'max:2000'],
            'resultado_optimizacion_id' => ['required', 'integer'],
            'sucursal_id' => ['required', 'integer'],
        ]);

        // El resultado debe pertenecer a esta lista (misma autorización que el
        // resto de recursos hijo: 404 si no existe dentro de la lista).
        $resultadoOptimizacion = ResultadoOptimizacion::query()
            ->where('lista_compra_id', $lista->id)
            ->where('id', $data['resultado_optimizacion_id'])
            ->first();

        if (! $resultadoOptimizacion) {
            abort(404, 'Corrida de optimización no encontrada.');
        }

        $guardado = $resultadoOptimizacion->resultado_json;
        $resultados = $guardado['resultados'] ?? [];
        $presupuesto = $guardado['presupuesto'] ?? null;

        $alternativa = collect($resultados)->first(
            fn ($r) => (int) ($r['sucursal_id'] ?? 0) === (int) $data['sucursal_id']
        );

        // Sin recomendación fiable → no tiene sentido preguntarle al asistente:
        // se devuelve el fallback sin llamar a /chat.
        $recommendation = $alternativa['recommendation'] ?? null;
        $disponible = is_array($recommendation)
            && ($alternativa['expert_system_available'] ?? false) === true;

        if (! $disponible) {
            return $this->chatNoDisponible();
        }

        $facts = $this->optimizationService->factsDesdeResultadoGuardado(
            $alternativa,
            $presupuesto,
            $lista->id,
            $resultados,
        );

        // El clasificador del experto es sensible a la redacción y no tiene una
        // intención para promociones. Se normaliza el tema antes de llamarlo.
        $pregunta = $this->chatIntentNormalizer->normalizar($data['message']);

        if ($pregunta['intent'] === 'PROMOCIONES') {
            return response()->json($this->respuestaPromociones(
                $facts,
                $alternativa['beneficio_promociones'] ?? 0,
            ));
        }

        $respuesta = $this->expertSystemService->chat([
            'message' => $pregunta['message'],
            'facts' => $facts,
            'recommendation' => $recommendation,
        ]);

        if (! $respuesta) {
            return $this->chatNoDisponible();
        }

        $respuesta['chatbot_available'] = true;

        return response()->json($respuesta);
    }

    /**
     * Respuesta determinista para el tema de promociones. Se usa mientras el
     * servicio Python no exponga esa intención (hoy responde AYUDA). No
     * inventa datos: solo interpreta los facts y la recomendación persistidos.
     *
     * @param  array<string, mixed>  $facts
     * @return array<string, mixed>
     */
    private function respuestaPromociones(array $facts, mixed $beneficioPromociones): array
    {
        $beneficio = is_numeric($beneficioPromociones) ? max(0, (float) $beneficioPromociones) : 0.0;

        if ($beneficio > 0) {
            $monto = '$'.number_format($beneficio, 2, '.', ',');
            $mensaje = 'Sí: esta sucursal tiene promociones aplicables a productos de tu lista. '
                .'El costo total ya refleja los precios promocionales; frente a los precios normales, '
                .'el beneficio registrado es de '.$monto.'.';
        } else {
            $mensaje = 'No se registraron promociones aplicables de los productos de tu lista en esta sucursal. '
                .'El costo mostrado no incluye descuentos por promoción.';
        }

        return [
            'request_id' => $facts['request_id'] ?? null,
            'intent' => 'PROMOCIONES',
            'response' => $mensaje,
            'supported' => true,
            'chatbot_available' => true,
        ];
    }

    private function chatNoDisponible(): \Illuminate\Http\JsonResponse
    {
        return response()->json([
            'request_id' => null,
            'intent' => 'NO_DISPONIBLE',
            'response' => 'El asistente explicativo no está disponible temporalmente. La recomendación principal continúa disponible.',
            'supported' => false,
            'chatbot_available' => false,
        ]);
    }

    // PATCH /api/listas/{lista}/completar
    // Marca la lista como compra realizada. Distingue "en progreso" de "ya comprada"
    // para poder construir el Historial de compras (Fase 5).
    public function completar(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $lista->update(['estado' => 'completada']);

        return $lista;
    }

    // PATCH /api/listas/{lista}/reactivar
    // Revierte una lista de completada a activa (undo de completar).
    // Sin esto, completar por error sería irreversible: no se puede volver
    // a comprar ni re-editar una lista marcada como comprada.
    public function reactivar(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $lista->update(['estado' => 'activa']);

        return $lista;
    }

    // GET /api/listas/{lista}/promociones
    // Cruza los productos de ESTA lista contra los precios con promoción activa.
    // Distinto de GET /api/promociones (que es general, sin filtrar por lista).
    public function promociones(ListaCompra $lista)
    {
        $this->verificarPropietario($lista);

        $productoIds = $lista->detalles()->pluck('producto_id');

        return \App\Models\PrecioActual::where('tiene_promocion', true)
            ->whereIn('producto_id', $productoIds)
            ->with(['producto.categoria', 'sucursal.supermercado'])
            ->get();
    }

}
