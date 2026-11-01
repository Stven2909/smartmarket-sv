<?php

namespace App\Providers;

use App\Models\PrecioActual;
use App\Observers\PrecioActualObserver;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Str;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        PrecioActual::observe(PrecioActualObserver::class);

        $this->configurarRateLimiting();
    }

    /**
     * Limites de peticiones de la API.
     *
     * - `api`: limite general por usuario autenticado o IP.
     * - `auth`: mas estricto para login/registro (mitiga fuerza bruta).
     * - `expert`: protege las llamadas costosas al Sistema Experto, que a su vez
     *   depende de un servicio externo con cold start.
     */
    private function configurarRateLimiting(): void
    {
        RateLimiter::for('api', function (Request $request) {
            return Limit::perMinute(60)->by($request->user()?->id ?: $request->ip());
        });

        RateLimiter::for('auth', function (Request $request) {
            return Limit::perMinute(5)->by(
                Str::lower((string) $request->input('email')).'|'.$request->ip()
            );
        });

        RateLimiter::for('expert', function (Request $request) {
            return Limit::perMinute(20)->by($request->user()?->id ?: $request->ip());
        });
    }
}
