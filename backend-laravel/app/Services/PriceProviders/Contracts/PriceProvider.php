<?php

namespace App\Services\PriceProviders\Contracts;

// Contrato de Price Provider (02-arquitectura.md §6.1 / ADR-006): cada fuente de
// precios implementa esto y el resto del sistema nunca sabe de dónde vienen los datos.
// Las filas que emite traen SOLO campos fácticos + raw_payload como evidencia (ADR-10).
interface PriceProvider
{
    // Clave de la fuente en config/price_providers.php ('walmart', 'super-selectos', ...)
    public function fuente(): string;

    // Modo de extracción ('vtex' | 'html')
    public function modo(): string;

    /**
     * Recolecta y emite filas crudas una a una (generador: no carga el catálogo
     * completo en memoria — Walmart ronda los 25k productos).
     *
     * Cada fila: nombre, unidad?, categoria_raw?, precio_normal?, precio_final,
     * tiene_promocion, disponible?, url_fuente?, raw_payload.
     */
    public function traer(): \Generator;
}
