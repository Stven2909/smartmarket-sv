<?php

namespace App\Services;

class NormalizadorTexto
{
    /*
     * Servicio meramente para limpieza de texto para las comparaciones: minusculas, palabras sin tildes,
     * sin caracteres especiales, espacios multiples, etc. Este servicio sirve para la parte de 'reglas simples'
     * del Motor de Normalizacion, mas adelante servira para decidir si un ProductoRaw corresponde a un Producto
     * que ya existe
     */
    public static function limpiar(string $texto): string
    {
        $texto = mb_strtolower(trim($texto));

        // Quita tildes/acentos comunes en español
        $texto = strtr($texto, [
            'á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ü' => 'u', 'ñ' => 'n',
        ]);

        // Quita caracteres que no sean letras, números o espacios
        $texto = preg_replace('/[^a-z0-9\s]/', ' ', $texto);

        // Colapsa espacios múltiples en uno solo
        $texto = preg_replace('/\s+/', ' ', $texto);

        return trim($texto);
    }

    /**
     * Extrae la presentación cuantificable de un nombre ("Leche entera 1 L",
     * "Café 500 g", "Jabón 3 x 110 g") y la devuelve en una unidad base
     * comparable: ml, g, lb, oz o un.
     *
     * Sirve como guardia del matching difuso: dos nombres pueden parecerse al
     * 95% y aun así ser productos distintos por presentación (1 L vs 2 L).
     * Devuelve null cuando el texto no declara una presentación reconocible.
     */
    public static function firmaUnidad(string $texto): ?string
    {
        // Se normaliza aparte de limpiar(): aquí los separadores decimales
        // importan ("1.5 L" no es "1" + "5 L").
        $texto = mb_strtolower(trim($texto));
        $texto = strtr($texto, [
            'á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ü' => 'u', 'ñ' => 'n',
        ]);
        $texto = preg_replace('/[^a-z0-9.,\s]/', ' ', $texto);
        $texto = preg_replace('/\s+/', ' ', $texto);

        $patron = '/(\d+(?:[.,]\d+)?)\s*(mililitros?|ml|litros?|lts|lt|l|kilogramos?|kilos?|kg|gramos?|gr|g|libras?|lbs|lb|onzas?|oz|unidades?|unds?|un)\b/';

        if (! preg_match($patron, $texto, $coincidencia)) {
            return null;
        }

        $cantidad = (float) str_replace(',', '.', $coincidencia[1]);

        [$unidadBase, $factor] = match ($coincidencia[2]) {
            'ml', 'mililitro', 'mililitros' => ['ml', 1.0],
            'l', 'lt', 'lts', 'litro', 'litros' => ['ml', 1000.0],
            'g', 'gr', 'gramo', 'gramos' => ['g', 1.0],
            'kg', 'kilo', 'kilos', 'kilogramo', 'kilogramos' => ['g', 1000.0],
            'lb', 'lbs', 'libra', 'libras' => ['lb', 1.0],
            'oz', 'onza', 'onzas' => ['oz', 1.0],
            'un', 'und', 'unds', 'unidad', 'unidades' => ['un', 1.0],
        };

        $valor = rtrim(rtrim(number_format($cantidad * $factor, 2, '.', ''), '0'), '.');

        return $valor.' '.$unidadBase;
    }

}

