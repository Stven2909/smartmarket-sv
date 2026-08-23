<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class ExpertSystemService
{
    /**
     * Envía un array de payloads al Sistema Experto y devuelve las
     * recomendaciones mapeadas por request_id.
     *
     * Cada item del array $payloads debe ser un associative array con los
     * 14 campos del contrato POST /api/v1/recommend.
     *
     * @param  array<int, array<string, mixed>>  $payloads
     * @return array<string, array<string, mixed>>|null  key = request_id
     */
    public function recommend(array $payloads): ?array
    {
        if ($payloads === []) {
            return [];
        }

        $url = rtrim(config('services.expert_system.url', 'https://sistema-experto-fork.onrender.com'), '/') . '/api/v1/recommend';

        $timeout = (int) config('services.expert_system.timeout', 3);
        $retryTimes = (int) config('services.expert_system.retry_times', 2);
        $retrySleep = (int) config('services.expert_system.retry_sleep_ms', 500);

        $resultados = [];

        foreach ($payloads as $payload) {
            $requestId = $payload['request_id'] ?? 'unknown';

            try {
                $response = Http::acceptJson()
                    ->asJson()
                    ->timeout($timeout)
                    ->retry($retryTimes, $retrySleep, throw: false)
                    ->post($url, $payload);

                if ($response->successful()) {
                    $body = $response->json();
                    $resultados[$requestId] = $body;
                } else {
                    Log::warning('ExpertSystem: respuesta no exitosa', [
                        'request_id' => $requestId,
                        'status' => $response->status(),
                        'endpoint' => $url,
                    ]);
                    $resultados[$requestId] = null;
                }
            } catch (\Throwable $e) {
                Log::warning('ExpertSystem: error en llamada', [
                    'request_id' => $requestId,
                    'error' => get_class($e) . ': ' . $e->getMessage(),
                    'endpoint' => $url,
                ]);
                $resultados[$requestId] = null;
            }
        }

        return $resultados;
    }
}
