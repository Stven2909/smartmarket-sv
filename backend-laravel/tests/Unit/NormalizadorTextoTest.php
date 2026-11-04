<?php

namespace Tests\Unit;

use App\Services\NormalizadorTexto;
use PHPUnit\Framework\TestCase;

class NormalizadorTextoTest extends TestCase
{
    public function test_firma_unidad_normaliza_litros_y_mililitros(): void
    {
        $this->assertSame('1000 ml', NormalizadorTexto::firmaUnidad('Leche entera 1 L'));
        $this->assertSame('1000 ml', NormalizadorTexto::firmaUnidad('Leche entera 1 litro'));
        $this->assertSame('900 ml', NormalizadorTexto::firmaUnidad('Detergente 900 ml'));
        $this->assertSame('1500 ml', NormalizadorTexto::firmaUnidad('Refresco 1.5 l'));
    }

    public function test_firma_unidad_normaliza_peso(): void
    {
        $this->assertSame('500 g', NormalizadorTexto::firmaUnidad('Café 500 g'));
        $this->assertSame('1000 g', NormalizadorTexto::firmaUnidad('Harina 1 kg'));
        $this->assertSame('2 lb', NormalizadorTexto::firmaUnidad('Arroz 2 lb'));
        $this->assertSame('110 g', NormalizadorTexto::firmaUnidad('Jabón 3 x 110 g'));
    }

    public function test_firma_unidad_devuelve_null_sin_presentacion_reconocible(): void
    {
        $this->assertNull(NormalizadorTexto::firmaUnidad('Pan blanco grande'));
        $this->assertNull(NormalizadorTexto::firmaUnidad(''));
    }
}
