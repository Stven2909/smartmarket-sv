<?php

declare(strict_types=1);

namespace Tests\Unit;

use App\Services\ExpertSystemClient;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

final class ExpertSystemClientTest extends TestCase
{
    public function testItReturnsRecommendationOnSuccess(): void
    {
        Http::fake([
            '*/api/v1/recommend' => Http::response([
                'request_id' => 'demo-001',
                'nivel_recomendacion' => 'EXCELENTE',
            ], 200),
        ]);

        $result = app(ExpertSystemClient::class)->recommend([
            'request_id' => 'demo-001',
        ]);

        $this->assertSame('EXCELENTE', $result['nivel_recomendacion']);
    }

    public function testItReturnsNullOnValidationFailure(): void
    {
        Http::fake([
            '*/api/v1/recommend' => Http::response(['detail' => 'invalid'], 422),
        ]);

        $this->assertNull(
            app(ExpertSystemClient::class)->recommend(['request_id' => 'invalid'])
        );
    }

    public function testFallbackPreservesLaravelOptimization(): void
    {
        Http::fake([
            '*/api/v1/recommend' => Http::response([], 500),
        ]);

        $fallback = ['optimized_total' => 42.50, 'expert_available' => false];
        $result = app(ExpertSystemClient::class)->recommendOrFallback([], $fallback);

        $this->assertSame($fallback, $result);
    }
}
