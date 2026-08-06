<?php

namespace App\Providers;

use App\Models\PrecioActual;
use Illuminate\Support\ServiceProvider;
use App\Observers\PrecioActualObserver;

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
        //
        PrecioActual::observe(PrecioActualObserver::class);
    }
}
