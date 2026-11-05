<?php

namespace App\Services;

// Valida la forma de las respuestas del Sistema Experto antes de persistirlas.
// El contrato vive en docs/CONTEXTO-SISTEMA-EXPERTO.md §5 y §9. Se aceptan
// campos extra (el servicio real agrega métricas auxiliares), pero se exigen
// los campos que la UI y el chat necesitan para explicar la recomendación.
class ExpertResponseValidator
{
    private const NIVELES = ['EXCELENTE', 'BUENA', 'NO_RECOMENDABLE'];

    /**
     * Devuelve la recomendación completa si cumple el contrato, o null si la
     * forma no es confiable. Nunca transforma ni inventa campos.
     *
     * @return array<string, mixed>|null
     */
    public function recommendation(mixed $body, ?string $expectedRequestId = null): ?array
    {
        if (! $this->esObjeto($body)) {
            return null;
        }

        if (! $this->textoNoVacio($body, 'request_id')
            || ! $this->textoNoVacio($body, 'accion_sugerida')
            || ! $this->textoNoVacio($body, 'explicacion')
            || ! $this->textoNoVacio($body, 'prioridad_aplicada')
            || ! $this->textoNoVacio($body, 'version_reglas')) {
            return null;
        }

        if ($expectedRequestId !== null && $body['request_id'] !== $expectedRequestId) {
            return null;
        }

        if (! is_string($body['nivel_recomendacion'] ?? null)
            || ! in_array($body['nivel_recomendacion'], self::NIVELES, true)) {
            return null;
        }

        if (! $this->listaDeTextos($body['reglas_activadas'] ?? null)
            || ! $this->listaDeTextos($body['losing_rules'] ?? null)) {
            return null;
        }

        if (! $this->esObjeto($body['hechos_derivados'] ?? null)
            || ! $this->valoresDeHechosValidos($body['hechos_derivados'])) {
            return null;
        }

        if (! array_key_exists('winning_rule', $body)
            || ($body['winning_rule'] !== null && ! $this->textoNoVacio($body, 'winning_rule'))) {
            return null;
        }

        if (! $this->trazaValida($body['trace'] ?? null)
            || ! $this->metricasOpcionalesValidas($body)) {
            return null;
        }

        return $body;
    }

    /**
     * Devuelve la respuesta del chat si cumple el contrato, o null.
     *
     * @return array<string, mixed>|null
     */
    public function chat(mixed $body, ?string $expectedRequestId = null): ?array
    {
        if (! $this->esObjeto($body)) {
            return null;
        }

        if (! $this->textoNoVacio($body, 'request_id')
            || ! $this->textoNoVacio($body, 'intent')
            || ! $this->textoNoVacio($body, 'response')
            || ! is_bool($body['supported'] ?? null)) {
            return null;
        }

        if ($expectedRequestId !== null && $body['request_id'] !== $expectedRequestId) {
            return null;
        }

        return $body;
    }

    private function esObjeto(mixed $value): bool
    {
        return is_array($value) && ! array_is_list($value);
    }

    private function textoNoVacio(array $body, string $key): bool
    {
        return is_string($body[$key] ?? null) && trim($body[$key]) !== '';
    }

    private function listaDeTextos(mixed $value): bool
    {
        if (! is_array($value) || ! array_is_list($value)) {
            return false;
        }

        foreach ($value as $item) {
            if (! is_string($item) || trim($item) === '') {
                return false;
            }
        }

        return true;
    }

    private function valoresDeHechosValidos(mixed $hechos): bool
    {
        if (! is_array($hechos)) {
            return false;
        }

        foreach ($hechos as $valor) {
            if (! is_bool($valor) && ! is_int($valor) && ! is_float($valor)) {
                return false;
            }
        }

        return true;
    }

    private function trazaValida(mixed $trace): bool
    {
        if (! is_array($trace) || ! array_is_list($trace)) {
            return false;
        }

        foreach ($trace as $step) {
            if (! is_array($step) || array_is_list($step)) {
                return false;
            }
        }

        return true;
    }

    /** @param array<string, mixed> $body */
    private function metricasOpcionalesValidas(array $body): bool
    {
        if (array_key_exists('indice_conveniencia', $body)
            && $body['indice_conveniencia'] !== null
            && (! $this->numeroFinito($body['indice_conveniencia'])
                || $body['indice_conveniencia'] < 0
                || $body['indice_conveniencia'] > 100)) {
            return false;
        }

        foreach (['clasificacion_conveniencia', 'version_contrato'] as $key) {
            if (array_key_exists($key, $body) && $body[$key] !== null && ! is_string($body[$key])) {
                return false;
            }
        }

        if (array_key_exists('chatbot_available', $body)
            && $body['chatbot_available'] !== null
            && ! is_bool($body['chatbot_available'])) {
            return false;
        }

        foreach (['componentes_conveniencia', 'pesos_conveniencia'] as $key) {
            if (array_key_exists($key, $body)
                && $body[$key] !== null
                && (! $this->esObjeto($body[$key]) || ! $this->mapaNumericoValido($body[$key]))) {
                return false;
            }
        }

        return true;
    }

    private function mapaNumericoValido(array $values): bool
    {
        foreach ($values as $value) {
            if (! $this->numeroFinito($value)) {
                return false;
            }
        }

        return true;
    }

    private function numeroFinito(mixed $value): bool
    {
        return is_int($value) || (is_float($value) && is_finite($value));
    }
}
