<?php

namespace App\Services\PriceProviders\Exceptions;

use RuntimeException;

// Señal de aborto de corrida (obligación 3 del ADR-10): el supermercado bloqueó
// el acceso o la saturación persistió tras los reintentos de cortesía.
// La corrida termina SIN evasión — no se resuelven captchas ni se rota identidad.
class FuenteBloqueadaException extends RuntimeException
{
    public static function porRespuesta(string $url, int $status): self
    {
        return new self("Bloqueo detectado en {$url} (HTTP {$status}). Corrida abortada sin evasión (ADR-10).");
    }

    public static function porSaturacionPersistente(string $url, int $status): self
    {
        return new self("HTTP {$status} persistente en {$url} tras agotar los reintentos de cortesía. Corrida abortada (ADR-10).");
    }
}
