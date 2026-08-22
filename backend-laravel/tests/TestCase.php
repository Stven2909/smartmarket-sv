<?php

namespace Tests;

use Illuminate\Contracts\Console\Kernel;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    // Laravel ya no incluye el trait CreatesApplication; sin este metodo
    // ninguna prueba que extienda Tests\TestCase puede bootear la aplicacion
    // (por eso las unicas pruebas previas eran PHPUnit plano, sin Laravel).
    public function createApplication()
    {
        $app = require __DIR__.'/../bootstrap/app.php';

        $app->make(Kernel::class)->bootstrap();

        return $app;
    }
}
