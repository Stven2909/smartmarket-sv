<?php

namespace App\Console\Commands;

use App\Models\AliasProducto;
use App\Models\Producto;
use App\Models\ProductoRaw;
use App\Services\NormalizadorTexto;
use Illuminate\Console\Command;

// Auditoría previa a cualquier cambio del Motor de Normalización (doc 06 §4).
// No modifica datos: reporta los problemas que hoy harían riesgoso automatizar
// más el matching — nombres duplicados, alias en conflicto, catálogo sin
// categoría/marca y la distribución real de similitud del staging pendiente.
class CatalogoAuditoria extends Command
{
    protected $signature = 'catalogo:auditoria
        {--limite=500 : Filas pendientes a muestrear para la distribución de similitud (0 = todas)}';

    protected $description = 'Reporta duplicados, alias en conflicto, productos incompletos y la distribución de similitud del staging pendiente';

    public function handle(): int
    {
        $productos = Producto::query()
            ->with('categoria:id,nombre')
            ->select('id', 'nombre', 'marca', 'categoria_id')
            ->orderBy('id')
            ->get();

        $alias = AliasProducto::query()
            ->select('id', 'producto_id', 'alias')
            ->orderBy('id')
            ->get();

        $porEstado = ProductoRaw::query()
            ->selectRaw('estado, count(*) as total')
            ->groupBy('estado')
            ->pluck('total', 'estado');

        $this->line('SmartMarket · Auditoría del catálogo y staging');
        $this->line(sprintf(
            'Productos: %d · Alias: %d · Filas pendientes: %d · En revisión manual: %d',
            $productos->count(),
            $alias->count(),
            (int) ($porEstado['pendiente'] ?? 0),
            (int) ($porEstado['revision_manual'] ?? 0),
        ));
        $this->newLine();

        $this->reportarNombresDuplicados($productos);
        $this->reportarAliasEnConflicto($alias);
        $this->reportarProductosIncompletos($productos);
        $this->reportarRevisionManual();
        $this->reportarDistribucionSimilitud($productos);

        return self::SUCCESS;
    }

    private function reportarNombresDuplicados($productos): void
    {
        $grupos = $productos->groupBy(fn (Producto $producto) => NormalizadorTexto::limpiar($producto->nombre))
            ->filter(fn ($grupo) => $grupo->count() > 1);

        $this->info("Nombres normalizados duplicados: {$grupos->count()}");

        if ($grupos->isEmpty()) {
            $this->line('  Sin duplicados por nombre normalizado.');
            $this->newLine();

            return;
        }

        $this->table(
            ['Nombre normalizado', 'Productos'],
            $grupos->map(fn ($grupo, string $clave) => [
                $clave,
                $grupo->map(fn (Producto $p) => "#{$p->id} {$p->nombre}")->implode(' | '),
            ])->values()->all(),
        );
        $this->newLine();
    }

    private function reportarAliasEnConflicto($alias): void
    {
        $conflictos = $alias
            ->groupBy(fn (AliasProducto $a) => NormalizadorTexto::limpiar($a->alias))
            ->map(fn ($grupo) => $grupo->pluck('producto_id')->unique()->values())
            ->filter(fn ($ids) => $ids->count() > 1);

        $this->info("Alias normalizados que apuntan a más de un producto: {$conflictos->count()}");

        if ($conflictos->isEmpty()) {
            $this->line('  Sin alias en conflicto.');
            $this->newLine();

            return;
        }

        $this->table(
            ['Alias normalizado', 'producto_id'],
            $conflictos->map(fn ($ids, string $clave) => [$clave, $ids->implode(', ')])->values()->all(),
        );
        $this->newLine();
    }

    private function reportarProductosIncompletos($productos): void
    {
        $sinMarca = $productos->filter(fn (Producto $p) => $p->marca === null || trim((string) $p->marca) === '' || $p->marca === 'Sin marca');
        $sinCategoria = $productos->filter(fn (Producto $p) => $p->categoria === null || $p->categoria->nombre === 'Otros');

        $this->info('Productos con datos incompletos');
        $this->line("  Sin marca útil: {$sinMarca->count()}");
        $this->line("  Sin categoría específica (Otros): {$sinCategoria->count()}");

        $muestra = $productos
            ->filter(fn (Producto $p) => $sinMarca->contains('id', $p->id) || $sinCategoria->contains('id', $p->id))
            ->take(15);

        if ($muestra->isNotEmpty()) {
            $this->table(
                ['id', 'nombre', 'marca', 'categoría'],
                $muestra->map(fn (Producto $p) => [
                    $p->id,
                    $p->nombre,
                    $p->marca ?: '—',
                    $p->categoria?->nombre ?? '—',
                ])->values()->all(),
            );
        }

        $this->newLine();
    }

    private function reportarRevisionManual(): void
    {
        $filas = ProductoRaw::query()
            ->where('estado', 'revision_manual')
            ->latest('id')
            ->limit(10)
            ->get(['id', 'nombre', 'fuente', 'motivo_rechazo']);

        $this->info('Cola de revisión manual (últimas 10 filas)');

        if ($filas->isEmpty()) {
            $this->line('  Sin filas pendientes de revisión.');
            $this->newLine();

            return;
        }

        $this->table(
            ['id', 'fuente', 'nombre', 'motivo'],
            $filas->map(fn (ProductoRaw $f) => [
                $f->id,
                $f->fuente,
                $f->nombre,
                $f->motivo_rechazo,
            ])->all(),
        );
        $this->newLine();
    }

    private function reportarDistribucionSimilitud($productos): void
    {
        $limite = max(0, (int) $this->option('limite'));

        $pendientes = ProductoRaw::query()
            ->where('estado', 'pendiente')
            ->orderBy('id')
            ->when($limite > 0, fn ($q) => $q->limit($limite))
            ->get(['id', 'nombre']);

        if ($pendientes->isEmpty()) {
            $this->info('Distribución de similitud: no hay filas pendientes para muestrear.');
            $this->newLine();

            return;
        }

        $catalogo = $productos->map(fn (Producto $p) => [
            'id' => $p->id,
            'nombre' => NormalizadorTexto::limpiar($p->nombre),
            'unidad' => NormalizadorTexto::firmaUnidad($p->nombre),
        ]);

        $buckets = [
            'exacto' => 0,
            '>= 95%' => 0,
            '90–94.9%' => 0,
            '85–89.9%' => 0,
            '< 85%' => 0,
        ];
        $ambiguos = 0;

        foreach ($pendientes as $fila) {
            $clave = NormalizadorTexto::limpiar($fila->nombre);
            $firma = NormalizadorTexto::firmaUnidad($fila->nombre);

            $mejor = 0.0;
            $segundo = 0.0;

            foreach ($catalogo as $candidato) {
                if ($firma !== null && $candidato['unidad'] !== null && $firma !== $candidato['unidad']) {
                    continue;
                }

                similar_text($clave, $candidato['nombre'], $porcentaje);

                if ($porcentaje > $mejor) {
                    $segundo = $mejor;
                    $mejor = $porcentaje;
                } elseif ($porcentaje > $segundo) {
                    $segundo = $porcentaje;
                }
            }

            $bucket = match (true) {
                $mejor >= 100.0 => 'exacto',
                $mejor >= 95.0 => '>= 95%',
                $mejor >= 90.0 => '90–94.9%',
                $mejor >= 85.0 => '85–89.9%',
                default => '< 85%',
            };
            $buckets[$bucket]++;

            if ($mejor >= 85.0 && $segundo >= 85.0 && ($mejor - $segundo) < 4.0) {
                $ambiguos++;
            }
        }

        $this->info("Distribución de similitud sobre {$pendientes->count()} fila(s) pendiente(s)");
        $this->table(
            ['Mejor similitud', 'Filas'],
            array_map(fn ($rango, $total) => [$rango, $total], array_keys($buckets), array_values($buckets)),
        );
        $this->line("  Coincidencias ambiguas (top-1 y top-2 a menos de 4 puntos): {$ambiguos}");
        $this->newLine();
    }
}
