"""Importación local CSV/JSON para la demo: sin dependencias ni cambios en FastAPI.

Los metadatos describen procedencia; el motor solo recibe los 14 hechos.
"""

import csv
import io
import json
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from urllib.parse import urlsplit

MAX_BYTES = 2_000_000
MAX_ROWS = 750

TEXT_FIELDS = ("request_id", "alternativa_id")
NUMERIC_FIELDS = (
    "costo_total", "presupuesto", "ahorro", "distancia_km",
    "distancia_adicional_km", "tiempo_estimado_min",
)
INTEGER_FIELDS = (
    "productos_disponibles", "productos_totales",
    "productos_esenciales_disponibles", "productos_esenciales_totales",
    "numero_supermercados",
)
BOOLEAN_FIELDS = ("promociones_aplicables",)
FACT_FIELDS = TEXT_FIELDS + NUMERIC_FIELDS + INTEGER_FIELDS + BOOLEAN_FIELDS
META_FIELDS = (
    "nombre", "procedencia", "fecha_observacion", "fuente_url",
    "tienda", "notas",
)
PROVENANCES = ("sintetico", "manual_real", "mixto_referencia_web")


@dataclass
class DatasetImport:
    scenarios: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_rows: int = 0


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name}: se espera número no negativo.")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{name}: es obligatorio.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}: se espera un número decimal válido.") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name}: no puede ser negativo ni infinito.")
    if name == "presupuesto" and number == 0:
        raise ValueError("presupuesto: debe ser mayor que cero.")
    return number


def _integer(value: Any, name: str) -> int:
    number = _number(value, name)
    if not number.is_integer():
        raise ValueError(f"{name}: debe ser un número entero.")
    if name in {"productos_totales", "numero_supermercados"} and number < 1:
        raise ValueError(f"{name}: debe ser mayor que cero.")
    return int(number)


def _boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower() if value is not None else ""
    if normalized in {"true", "1", "si", "sí", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError("promociones_aplicables: use true/false, sí/no o 1/0.")


def _valid_date(text: str) -> bool:
    try:
        return date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def _valid_url(text: str) -> bool:
    parts = urlsplit(text)
    return parts.scheme == "https" and bool(parts.netloc) and not parts.username


def _read_rows(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    if len(file_bytes) > MAX_BYTES:
        raise ValueError("El archivo supera el límite de 2 MB.")
    if not file_bytes:
        raise ValueError("El archivo está vacío.")
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Utilice un archivo UTF-8.") from exc

    name = filename.lower().strip()
    if name.endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
            headers = reader.fieldnames or []
            if not headers or any(not name for name in headers):
                raise ValueError("El CSV requiere encabezados válidos.")
            if len(headers) != len(set(headers)):
                raise ValueError("El CSV tiene encabezados duplicados.")
            rows = []
            for row in reader:
                rows.append(row)
                if len(rows) > MAX_ROWS:
                    raise ValueError("El archivo supera el máximo de 750 filas.")
            return rows
        except csv.Error as exc:
            raise ValueError(f"CSV mal formado: {exc}") from exc

    if name.endswith(".json"):
        try:
            value = json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(
                ValueError(f"Valor JSON no finito: {x}")
            ))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON inválido, línea {exc.lineno}, columna {exc.colno}."
            ) from exc
        if isinstance(value, dict):
            value = value.get("escenarios")
        if not isinstance(value, list):
            raise ValueError("JSON debe contener una lista o un objeto con 'escenarios'.")
        if len(value) > MAX_ROWS:
            raise ValueError("El archivo supera el máximo de 750 filas.")
        return value
    raise ValueError("Formato no compatible: use CSV o JSON.")


def _parse_scenario(raw: Any, position: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("cada fila debe ser un objeto.")
    # El CSV contiene hechos planos; JSON también admite {nombre, facts}.
    if "facts" in raw:
        facts = raw["facts"]
        metadata = {key: value for key, value in raw.items() if key != "facts"}
    else:
        facts = {key: raw[key] for key in FACT_FIELDS if key in raw}
        metadata = {key: raw[key] for key in META_FIELDS if key in raw}
    if not isinstance(facts, dict):
        raise ValueError("facts debe ser un objeto con los 14 hechos.")
    missing = [key for key in FACT_FIELDS if key not in facts or facts[key] is None]
    if missing:
        raise ValueError("faltan campos: " + ", ".join(missing))
    unknown = sorted(set(facts) - set(FACT_FIELDS))
    if unknown:
        raise ValueError("campos adicionales no admitidos: " + ", ".join(unknown))
    if any(value is None for value in metadata.values()):
        raise ValueError("metadatos incompletos: revise las columnas.")
    converted: dict[str, Any] = {}
    for key in TEXT_FIELDS:
        val = facts[key]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"{key}: debe ser un texto no vacío.")
        converted[key] = val.strip()
    for key in NUMERIC_FIELDS:
        converted[key] = _number(facts[key], key)
    for key in INTEGER_FIELDS:
        converted[key] = _integer(facts[key], key)
    converted["promociones_aplicables"] = _boolean(facts["promociones_aplicables"])

    available = converted["productos_disponibles"]
    total = converted["productos_totales"]
    ess_available = converted["productos_esenciales_disponibles"]
    ess_total = converted["productos_esenciales_totales"]
    if available > total or ess_available > ess_total or ess_total > total:
        raise ValueError("los conteos de productos/esenciales superan su total.")
    if ess_available > available or available - ess_available > total - ess_total:
        raise ValueError("los conteos opcionales/esenciales son inconsistentes.")

    provenance = str(metadata.get("procedencia") or "sintetico").strip().lower()
    if provenance not in PROVENANCES:
        raise ValueError(
            "procedencia: use sintetico, manual_real o mixto_referencia_web."
        )
    observed = str(metadata.get("fecha_observacion") or "").strip()
    source = str(metadata.get("fuente_url") or "").strip()
    store = str(metadata.get("tienda") or "").strip()
    notes = str(metadata.get("notas") or "").strip()
    if observed and not _valid_date(observed):
        raise ValueError("fecha_observacion: use formato YYYY-MM-DD.")
    if source and not _valid_url(source):
        raise ValueError("fuente_url: use un enlace HTTPS válido.")
    if provenance == "manual_real" and (not observed or not store):
        raise ValueError(
            "manual_real requiere fecha_observacion y tienda; "
            "la aplicación no verifica la autenticidad."
        )
    if provenance == "mixto_referencia_web" and (not observed or not source):
        raise ValueError(
            "mixto_referencia_web requiere fecha_observacion y fuente_url."
        )
    name = str(metadata.get("nombre") or converted["alternativa_id"]).strip()
    if not name:
        raise ValueError("nombre: debe ser un texto no vacío.")
    return {
        "id": converted["alternativa_id"],
        "name": name[:120],
        "facts": converted,
        "metadata": {
            "procedencia": provenance,
            "fecha_observacion": observed,
            "fuente_url": source,
            "tienda": store,
            "notas": notes,
        },
    }


def import_dataset(file_bytes: bytes, filename: str) -> DatasetImport:
    """Validación por fila; cero llamadas HTTP y cero almacenamiento persistente."""

    result = DatasetImport()
    try:
        rows = _read_rows(file_bytes, filename)
    except ValueError as exc:
        result.errors.append(str(exc))
        return result
    if not rows:
        result.errors.append("No se encontraron alternativas.")
        return result
    result.total_rows = len(rows)
    seen: set[str] = set()
    for position, raw in enumerate(rows, start=2):
        try:
            item = _parse_scenario(raw, position)
            identifier = item["facts"]["alternativa_id"]
            if identifier in seen:
                raise ValueError(f"alternativa_id duplicado: {identifier}.")
            seen.add(identifier)
            result.scenarios.append(item)
        except (ValueError, TypeError) as exc:
            if len(result.errors) < 30:
                result.errors.append(f"Fila {position}: {exc}")
    if result.errors:
        # Un fichero parcialmente inválido no puede pasar silenciosamente al motor.
        result.scenarios.clear()
        if len(result.errors) == 30:
            result.errors.append("Se muestran como máximo 30 errores.")
        return result

    kinds = {item["metadata"]["procedencia"] for item in result.scenarios}
    if "manual_real" in kinds:
        result.warnings.append(
            "Los datos etiquetados manual_real son declarados por quien cargó el archivo; "
            "su autenticidad y vigencia no fueron verificadas por SmartMarket."
        )
    if "mixto_referencia_web" in kinds:
        result.warnings.append(
            "Los escenarios mixtos contienen hechos simulados: la fuente web "
            "no verifica distancias, ahorros ni existencias de una compra completa."
        )
    budgets = {item["facts"]["presupuesto"] for item in result.scenarios}
    if len(budgets) > 1:
        result.warnings.append(
            "Hay presupuestos distintos. Selecciona alternativas con el mismo "
            "presupuesto antes de comparar."
        )
    return result
