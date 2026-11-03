"""HU-21: read-only check of Laravel's live producer against the Python contract.

Nothing is changed in develop, the Laravel application or any live service.
This script is intended for development/CI, not for the FastAPI request path.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.recommendation import RecommendationRequest

UPSTREAM_BASE = (
    "https://raw.githubusercontent.com/Stven2909/smartmarket-sv/develop/"
    "backend-laravel/"
)
PRODUCER_PATH = "app/Services/Optimization/OptimizationService.php"
CLIENT_PATH = "app/Services/ExpertSystemService.php"


def payload_fields_from_php(source: str) -> list[str]:
    """Read keys from construirPayload's return array; fail closed if it moves."""
    function = re.search(r"\bfunction\s+construirPayload\s*\(", source)
    if function is None:
        raise ValueError("No existe el método construirPayload.")

    block = re.search(
        r"(?ms)^\s*return\s*\[\s*(.*?)^\s*\];",
        source[function.end():],
    )
    if block is None:
        raise ValueError("No se pudo localizar el return array de construirPayload.")

    fields = re.findall(r"(?m)^\s*'([a-z][a-z0-9_]*)'\s*=>", block.group(1))
    if not fields or len(fields) != len(set(fields)):
        raise ValueError("El payload no contiene claves únicas reconocibles.")
    return fields


def validate_php_contract(producer: str, client: str) -> None:
    """Raise with an actionable message when Laravel and Python have drifted."""
    actual = set(payload_fields_from_php(producer))
    expected = set(RecommendationRequest.model_fields)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        raise ValueError(
            f"Contrato Laravel/Python incompatible: faltantes={missing}; "
            f"inesperados={unexpected}."
        )

    if "/api/v1/recommend" not in client or "->post($url, $payload)" not in client:
        raise ValueError("El cliente PHP ya no envía el payload a /api/v1/recommend.")
    if "X-API-Key" not in client:
        raise ValueError("El cliente PHP no expone el encabezado X-API-Key.")
    if "$requestId = $payload['request_id']" not in client:
        raise ValueError("No se encontró la correlación request_id en el cliente PHP.")


def _fetch_upstream(path: str) -> str:
    url = UPSTREAM_BASE + path
    req = Request(url, headers={"User-Agent": "SmartMarket-Expert-Contract-CI/1.0"})
    with urlopen(req, timeout=15) as response:
        return response.read().decode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", action="store_true", help="Read current public develop from GitHub")
    parser.add_argument("--producer-file", type=Path, help="Local OptimizationService.php")
    parser.add_argument("--client-file", type=Path, help="Local ExpertSystemService.php")
    args = parser.parse_args(argv)

    if args.upstream == bool(args.producer_file or args.client_file):
        parser.error("Use --upstream OR both --producer-file and --client-file.")
    if not args.upstream and not (args.producer_file and args.client_file):
        parser.error("Both --producer-file and --client-file are required for local mode.")

    try:
        if args.upstream:
            producer = _fetch_upstream(PRODUCER_PATH)
            client = _fetch_upstream(CLIENT_PATH)
        else:
            producer = args.producer_file.read_text(encoding="utf-8")
            client = args.client_file.read_text(encoding="utf-8")
        validate_php_contract(producer, client)
    except (ValueError, OSError, HTTPError, URLError, UnicodeDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: Laravel develop genera los 14 campos del contrato Python; "
        "endpoint, correlación y X-API-Key reconocidos. Solo lectura."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
