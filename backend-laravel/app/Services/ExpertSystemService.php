<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
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
     * @return array<string, array<string, mixed>>|null key = request_id
     */
    public function recommend(array $payloads): ?array
    {
        if ($payloads === []) {
            return [];
        }

        $url = rtrim(config('services.expert_system.url', 'https://sistema-experto-fork.onrender.com'), '/').'/api/v1/recommend';

        $resultados = [];

        foreach ($payloads as $payload) {
            $requestId = $payload['request_id'] ?? 'unknown';

            try {
                $response = $this->httpClient()->post($url, $payload);

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
                    'error' => get_class($e).': '.$e->getMessage(),
                    'endpoint' => $url,
                ]);
                $resultados[$requestId] = null;
            }
        }

        return $resultados;
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
     */
    public function chat(array $payload): ?array
    {
        $url = rtrim(config('services.expert_system.url', 'https://sistema-experto-fork.onrender.com'), '/').'/api/v1/chat';

        try {
            $response = $this->httpClient()->post($url, $payload);

            if ($response->successful()) {
                return $response->json();
            }

            Log::warning('ExpertSystem: chat no exitoso', [
                'status' => $response->status(),
                'endpoint' => $url,
            ]);

            return null;
        } catch (\Throwable $e) {
            Log::warning('ExpertSystem: error en llamada de chat', [
                'error' => get_class($e).': '.$e->getMessage(),
                'endpoint' => $url,
            ]);

            return null;
        }
    }

    /**
     * Cliente HTTP base para el Sistema Experto. Envía X-API-Key únicamente
     * cuando la variable EXPERT_SYSTEM_API_KEY está configurada, para no
     * romper el flujo local/desarrollo que funciona sin ella.
     */
    private function httpClient(): PendingRequest
    {
        $client = Http::acceptJson()
            ->asJson()
            ->timeout((int) config('services.expert_system.timeout', 3))
            ->retry(
                (int) config('services.expert_system.retry_times', 2),
                (int) config('services.expert_system.retry_sleep_ms', 500),
                throw: false,
            );

        $apiKey = config('services.expert_system.api_key');

        if (is_string($apiKey) && $apiKey !== '') {
            $client = $client->withHeaders(['X-API-Key' => $apiKey]);
        }

        return $client;
    }
}
