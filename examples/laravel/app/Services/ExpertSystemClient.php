<?php

declare(strict_types=1);

namespace App\Services;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

final class ExpertSystemClient
{
    private readonly string $baseUrl;
    private readonly int $timeoutSeconds;
    private readonly int $retryTimes;

    public function __construct()
    {
        $this->baseUrl = rtrim((string) config('services.expert_system.url'), '/');
        $this->timeoutSeconds = max(1, (int) config('services.expert_system.timeout', 3));
        $this->retryTimes = max(0, (int) config('services.expert_system.retry_times', 1));
    }

    /**
     * @param array<string, mixed> $facts
     * @return array<string, mixed>|null
     */
    public function recommend(array $facts): ?array
    {
        return $this->post('/api/v1/recommend', $facts);
    }

    /**
     * @param array<string, mixed> $payload
     * @return array<string, mixed>|null
     */
    public function chat(array $payload): ?array
    {
        return $this->post('/api/v1/chat', $payload);
    }

    /**
     * Keeps Laravel's optimization result as the fallback.
     *
     * @param array<string, mixed> $facts
     * @param array<string, mixed> $optimizationResult
     * @return array<string, mixed>
     */
    public function recommendOrFallback(
        array $facts,
        array $optimizationResult,
    ): array {
        return $this->recommend($facts) ?? $optimizationResult;
    }

    /**
     * @param array<string, mixed> $payload
     * @return array<string, mixed>|null
     */
    private function post(string $path, array $payload): ?array
    {
        try {
            $response = Http::acceptJson()
                ->asJson()
                ->timeout($this->timeoutSeconds)
                ->retry($this->retryTimes, 100, throw: false)
                ->post($this->baseUrl . $path, $payload);
        } catch (ConnectionException|RequestException $exception) {
            Log::warning('Expert System request failed', [
                'endpoint' => $path,
                'error_type' => $exception::class,
            ]);

            return null;
        }

        if ($response->successful()) {
            $json = $response->json();

            return is_array($json) ? $json : null;
        }

        Log::warning('Expert System returned non-success status', [
            'endpoint' => $path,
            'status' => $response->status(),
        ]);

        return null;
    }
}
