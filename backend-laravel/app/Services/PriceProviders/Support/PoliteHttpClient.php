<?php

namespace App\Services\PriceProviders\Support;

use App\Services\PriceProviders\Exceptions\FuenteBloqueadaException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

// Cliente HTTP compartido por todos los drivers, con la cortesía obligatoria
// del ADR-10 (docs/07-decision-extractor-fuentes-riesgo.md):
//
// - User-Agent identificable — nunca suplantar un navegador.
// - Pausa configurable entre requests consecutivos (default 1500 ms).
// - Reintentos acotados con backoff exponencial SOLO ante 429/503.
// - Bloqueo/captcha detectado o 429/503 persistente ⇒ aborta la corrida
//   completa lanzando FuenteBloqueadaException. Sin evasión jamás.
class PoliteHttpClient
{
    private ?float $ultimaPeticionAt = null;

    public function get(string $url, array $query = []): Response
    {
        $this->pausar();

        $response = $this->enviar($url, $query);

        $this->ultimaPeticionAt = microtime(true);

        return $response;
    }

    // Cortesía central: garantiza el espacio mínimo entre peticiones hacia la
    // misma corrida. La primera petición del proceso no espera.
    private function pausar(): void
    {
        if ($this->ultimaPeticionAt === null) {
            return;
        }

        $pausaMs = (int) config('price_providers.defaults.pausa_ms', 1500);
        $transcurridoMs = (microtime(true) - $this->ultimaPeticionAt) * 1000;

        if ($transcurridoMs < $pausaMs) {
            usleep((int) round(($pausaMs - $transcurridoMs) * 1000));
        }
    }

    private function enviar(string $url, array $query): Response
    {
        $maxReintentos = (int) config('price_providers.defaults.reintentos', 3);
        $backoffMs = (int) config('price_providers.defaults.backoff_ms', 500);
        $intento = 0;

        while (true) {
            $response = Http::withHeaders($this->headers())
                ->timeout((int) config('price_providers.defaults.timeout_segundos', 30))
                ->get($url, $query);

            // Bloqueo explícito del supermercado: abortar sin evasión.
            if ($this->detectarBloqueo($response)) {
                throw FuenteBloqueadaException::porRespuesta($url, $response->status());
            }

            // Cualquier otra respuesta se deja evaluar al driver (incluye otros
            // 4xx/5xx); solo 429/503 tienen tratamiento de cortesía.
            if (! in_array($response->status(), [429, 503], true)) {
                return $response;
            }

            $intento++;

            if ($intento > $maxReintentos) {
                throw FuenteBloqueadaException::porSaturacionPersistente($url, $response->status());
            }

            // Backoff exponencial: 500ms, 1s, 2s...
            usleep($backoffMs * 1000 * 2 ** ($intento - 1));
        }
    }

    private function headers(): array
    {
        return [
            'User-Agent' => (string) config('price_providers.defaults.user_agent'),
            'Accept' => 'application/json, text/html;q=0.8, */*;q=0.5',
            'Accept-Language' => 'es-SV,es;q=0.9',
        ];
    }

    private function detectarBloqueo(Response $response): bool
    {
        if ($response->status() === 403) {
            return true;
        }

        // Señales típicas de desafío anti-bot en el cuerpo (se revisa solo el
        // inicio de la respuesta: suficiente para páginas de challenge).
        $inicio = strtolower(substr($response->body() ?? '', 0, 5000));

        foreach (['captcha', 'verify you are human', 'access denied', 'cf-browser-verification'] as $senal) {
            if (str_contains($inicio, $senal)) {
                return true;
            }
        }

        return false;
    }
}
