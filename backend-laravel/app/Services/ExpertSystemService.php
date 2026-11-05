<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ExpertSystemService
{
    public function __construct(
        private ExpertResponseValidator $validator,
    ) {}

    /**
     * Envía un array de payloads al Sistema Experto y devuelve las
     * recomendaciones validadas, los motivos de omisión y la duración total.
     *
     * Cada item del array $payloads debe ser un associative array con los
     * 14 campos del contrato POST /api/v1/recommend.
     *
     * @param  array<int, array<string, mixed>>  $payloads
     * @return array{
     *     respuestas: array<string, array<string, mixed>|null>,
     *     motivos: array<string, string|null>,
     *     duracion_ms: int
     * }
     */
    public function recommend(array $payloads): array
    {
        if ($payloads === []) {
            return ['respuestas' => [], 'motivos' => [], 'duracion_ms' => 0];
        }

        $url = $this->url('/api/v1/recommend');
        $deadline = $this->deadline();
        $inicio = $this->ahoraMs();

        $respuestas = [];
        $motivos = [];

        foreach ($payloads as $payload) {
            $requestId = (string) ($payload['request_id'] ?? 'unknown');

            $resultado = $this->post($url, $payload, $deadline, [
                'endpoint' => 'recommend',
                'request_id' => $requestId,
            ]);

            if ($resultado['respuesta'] === null) {
                $respuestas[$requestId] = null;
                $motivos[$requestId] = $resultado['motivo'] ?? 'sin_respuesta';

                continue;
            }

            $validada = $this->validator->recommendation($resultado['respuesta'], $requestId);

            if ($validada === null) {
                $respuestas[$requestId] = null;
                $motivos[$requestId] = 'respuesta_invalida';

                Log::warning('ExpertSystem: recomendación con forma inválida', [
                    'request_id' => $requestId,
                    'status' => $resultado['status'],
                    'duracion_ms' => $resultado['duracion_ms'],
                ]);

                continue;
            }

            $respuestas[$requestId] = $validada;
            $motivos[$requestId] = null;
        }

        $duracionMs = $this->ahoraMs() - $inicio;

        Log::info('ExpertSystem: lote de recomendaciones procesado', [
            'alternativas' => count($payloads),
            'exitosas' => count(array_filter($respuestas, 'is_array')),
            'omitidas' => count(array_filter($motivos, 'is_string')),
            'duracion_ms' => $duracionMs,
            'presupuesto_ms' => (int) config('services.expert_system.total_budget_ms', 25000),
        ]);

        return [
            'respuestas' => $respuestas,
            'motivos' => $motivos,
            'duracion_ms' => $duracionMs,
        ];
    }

    /**
     * Envía una pregunta explicativa al asistente del Sistema Experto.
     *
     * El payload debe incluir 'message', 'facts' (los 14 campos del contrato
     * POST /api/v1/recommend) y 'recommendation' (la respuesta completa que
     * devolvió /recommend para la alternativa sobre la que se pregunta).
     *
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>|null null si el asistente no está disponible
     *                                       o su respuesta no cumple el contrato
     */
    public function chat(array $payload): ?array
    {
        $url = $this->url('/api/v1/chat');
        $requestId = isset($payload['facts']['request_id']) && is_string($payload['facts']['request_id'])
            ? $payload['facts']['request_id']
            : null;

        $resultado = $this->post($url, $payload, $this->deadline(), [
            'endpoint' => 'chat',
            'request_id' => $requestId,
        ]);

        if ($resultado['respuesta'] === null) {
            return null;
        }

        $validada = $this->validator->chat($resultado['respuesta'], $requestId);

        if ($validada === null) {
            Log::warning('ExpertSystem: respuesta de chat con forma inválida', [
                'request_id' => $requestId,
                'status' => $resultado['status'],
                'duracion_ms' => $resultado['duracion_ms'],
            ]);

            return null;
        }

        return $validada;
    }

    /**
     * POST con timeout de conexión, timeout por intento, reintentos selectivos
     * (solo 429/5xx/conexión) y un presupuesto total compartido por la corrida.
     *
     * @param  array<string, mixed>  $payload
     * @param  array{endpoint: string, request_id?: string|null}  $contexto
     * @return array{respuesta: mixed, motivo: string|null, status: int|null, intentos: int, duracion_ms: int}
     */
    private function post(string $url, array $payload, ?float $deadline, array $contexto): array
    {
        $maxIntentos = max(1, (int) config('services.expert_system.retry_times', 3));
        $esperaBaseMs = max(0, (int) config('services.expert_system.retry_sleep_ms', 2000));
        $timeout = max(0.1, (float) config('services.expert_system.timeout', 15));
        $connectTimeout = max(0.1, (float) config('services.expert_system.connect_timeout', 5));
        $inicio = $this->ahoraMs();

        for ($intento = 1; $intento <= $maxIntentos; $intento++) {
            if ($deadline !== null && microtime(true) >= $deadline) {
                return $this->resultado(null, 'presupuesto_agotado', null, $intento - 1, $inicio);
            }

            $restante = $deadline !== null ? max(0.1, $deadline - microtime(true)) : null;
            $timeoutIntento = $restante !== null ? min($timeout, $restante) : $timeout;
            $connectIntento = $restante !== null ? min($connectTimeout, $restante) : $connectTimeout;
            $inicioIntento = $this->ahoraMs();

            try {
                $response = $this->httpClient($timeoutIntento, $connectIntento)->post($url, $payload);
                $status = $response->status();

                if ($response->successful()) {
                    Log::info('ExpertSystem: respuesta recibida', [
                        ...$contexto,
                        'status' => $status,
                        'intento' => $intento,
                        'duracion_ms' => $this->ahoraMs() - $inicioIntento,
                    ]);

                    return $this->resultado($response->json(), null, $status, $intento, $inicio);
                }

                $reintentable = $status === 429 || $status >= 500;
                $esperaMs = $this->esperaMs($response, $esperaBaseMs, $intento);
                $puedeReintentar = $reintentable
                    && $intento < $maxIntentos
                    && $this->hayTiempoPara($deadline, $esperaMs);

                if ($puedeReintentar) {
                    usleep($esperaMs * 1000);

                    continue;
                }

                $motivo = $reintentable && ! $this->hayTiempoPara($deadline, $esperaMs)
                    ? 'presupuesto_agotado'
                    : 'sin_respuesta';

                Log::warning('ExpertSystem: respuesta no exitosa', [
                    ...$contexto,
                    'status' => $status,
                    'intento' => $intento,
                    'motivo' => $motivo,
                    'reintentable' => $reintentable,
                    'duracion_ms' => $this->ahoraMs() - $inicioIntento,
                ]);

                return $this->resultado(null, $motivo, $status, $intento, $inicio);
            } catch (\Throwable $e) {
                $esperaMs = $esperaBaseMs * $intento;
                $puedeReintentar = $intento < $maxIntentos && $this->hayTiempoPara($deadline, $esperaMs);

                if ($puedeReintentar) {
                    usleep($esperaMs * 1000);

                    continue;
                }

                $motivo = $this->hayTiempoPara($deadline, $esperaMs)
                    ? 'sin_respuesta'
                    : 'presupuesto_agotado';

                Log::warning('ExpertSystem: error en llamada', [
                    ...$contexto,
                    'error' => get_class($e).': '.$e->getMessage(),
                    'intento' => $intento,
                    'motivo' => $motivo,
                    'duracion_ms' => $this->ahoraMs() - $inicioIntento,
                ]);

                return $this->resultado(null, $motivo, null, $intento, $inicio);
            }
        }

        return $this->resultado(null, 'sin_respuesta', null, $maxIntentos, $inicio);
    }

    /**
     * Cliente HTTP base para el Sistema Experto. Envía X-API-Key únicamente
     * cuando la variable EXPERT_SYSTEM_API_KEY está configurada, para no
     * romper el flujo local/desarrollo que funciona sin ella.
     */
    private function httpClient(float $timeout, float $connectTimeout): PendingRequest
    {
        $client = Http::acceptJson()
            ->asJson()
            ->connectTimeout($connectTimeout)
            ->timeout($timeout);

        $apiKey = config('services.expert_system.api_key');

        if (is_string($apiKey) && $apiKey !== '') {
            $client = $client->withHeaders(['X-API-Key' => $apiKey]);
        }

        return $client;
    }

    private function url(string $path): string
    {
        return rtrim(config('services.expert_system.url', 'https://sistema-experto-fork.onrender.com'), '/').$path;
    }

    private function deadline(): ?float
    {
        $presupuestoMs = (int) config('services.expert_system.total_budget_ms', 25000);

        if ($presupuestoMs <= 0) {
            return null;
        }

        return microtime(true) + ($presupuestoMs / 1000);
    }

    private function hayTiempoPara(?float $deadline, int $esperaMs): bool
    {
        if ($deadline === null) {
            return true;
        }

        return (microtime(true) + ($esperaMs / 1000)) < $deadline;
    }

    private function esperaMs(\Illuminate\Http\Client\Response $response, int $baseMs, int $intento): int
    {
        $retryAfter = $response->header('Retry-After');

        if (is_numeric($retryAfter)) {
            return min(5000, max($baseMs, (int) ceil((float) $retryAfter * 1000)));
        }

        return min(5000, $baseMs * $intento);
    }

    /**
     * @return array{respuesta: mixed, motivo: string|null, status: int|null, intentos: int, duracion_ms: int}
     */
    private function resultado(mixed $respuesta, ?string $motivo, ?int $status, int $intentos, int $inicioMs): array
    {
        return [
            'respuesta' => $respuesta,
            'motivo' => $motivo,
            'status' => $status,
            'intentos' => $intentos,
            'duracion_ms' => $this->ahoraMs() - $inicioMs,
        ];
    }

    private function ahoraMs(): int
    {
        return (int) floor(hrtime(true) / 1_000_000);
    }
}
