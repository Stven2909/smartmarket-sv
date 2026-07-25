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

}

