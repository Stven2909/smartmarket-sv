"""Non-intrusive external security smoke test (4 GETs, no API key).

Run manually against a service you control. Never tests brute force or load.
It checks the public health route and refusal of anonymous business/docs access.
"""

import argparse
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

CHECKS = (
    ("/health", frozenset({200})),
    ("/api/v1/knowledge", frozenset({401})),
    ("/docs", frozenset({404})),
    ("/openapi.json", frozenset({404})),
)


def probe(base_url: str) -> list[str]:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Usa una URL base HTTPS sin ruta, credenciales ni parámetros.")

    failures: list[str] = []
    for path, expected in CHECKS:
        url = base_url.rstrip("/") + path
        request = Request(
            url,
            method="GET",
            headers={"User-Agent": "SmartMarket-Authorized-Security-Smoke/1.0"},
        )
        try:
            with urlopen(request, timeout=25) as response:
                actual = response.status
        except HTTPError as exc:
            actual = exc.code
        except (URLError, TimeoutError, OSError) as exc:
            failures.append(f"{path}: no se pudo conectar ({type(exc).__name__})")
            continue
        if actual not in expected:
            failures.append(f"{path}: HTTP {actual}; esperado {sorted(expected)}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="URL HTTPS de tu FastAPI")
    args = parser.parse_args(argv)
    try:
        errors = probe(args.base_url)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("NO APROBADO: " + " | ".join(errors))
        return 1
    print(
        "APROBADO: /health pública, /api/v1/knowledge rechaza acceso anónimo "
        "y documentación OpenAPI oculta."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
