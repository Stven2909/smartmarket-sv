from app.schemas.recommendation import RecommendationRequest


# Umbrales de clasificación. Las reglas del futuro motor consumirán los
# hechos resultantes, sin repetir estas comparaciones numéricas.
THRESHOLDS_VERSION = "1.0.0"

THRESHOLDS = {
    "presupuesto_exceso_max_pct": 10.0,
    "ahorro_bajo_max": 3.0,
    "ahorro_alto_min": 10.0,
    "distancia_cercana_max_km": 2.0,
    "distancia_media_max_km": 8.0,
    "tiempo_bajo_max_min": 20.0,
    "tiempo_medio_max_min": 45.0,
    "compra_fragmentada_min_supermercados": 3,
}


def derive_facts(request: RecommendationRequest) -> dict[str, bool | float]:
    """Convierte una solicitud validada en hechos booleanos y métricas útiles."""

    diferencia_presupuesto = request.presupuesto - request.costo_total
    porcentaje_exceso_presupuesto = max(
        0.0,
        (request.costo_total - request.presupuesto) / request.presupuesto * 100,
    )
    porcentaje_productos_disponibles = (
        request.productos_disponibles / request.productos_totales * 100
    )
    porcentaje_esenciales_disponibles = (
        request.productos_esenciales_disponibles
        / request.productos_esenciales_totales
        * 100
    )

    dentro_presupuesto = request.costo_total <= request.presupuesto
    presupuesto_ligeramente_excedido = (
        not dentro_presupuesto
        and porcentaje_exceso_presupuesto
        <= THRESHOLDS["presupuesto_exceso_max_pct"]
    )
    presupuesto_muy_excedido = (
        porcentaje_exceso_presupuesto
        > THRESHOLDS["presupuesto_exceso_max_pct"]
    )

    todos_productos_disponibles = (
        request.productos_disponibles == request.productos_totales
    )
    todos_esenciales_disponibles = (
        request.productos_esenciales_disponibles
        == request.productos_esenciales_totales
    )

    ahorro_bajo = request.ahorro < THRESHOLDS["ahorro_bajo_max"]
    ahorro_medio = (
        THRESHOLDS["ahorro_bajo_max"]
        <= request.ahorro
        < THRESHOLDS["ahorro_alto_min"]
    )
    ahorro_alto = request.ahorro >= THRESHOLDS["ahorro_alto_min"]

    distancia_cercana = (
        request.distancia_adicional_km
        <= THRESHOLDS["distancia_cercana_max_km"]
    )
    distancia_media = (
        THRESHOLDS["distancia_cercana_max_km"]
        < request.distancia_adicional_km
        < THRESHOLDS["distancia_media_max_km"]
    )
    distancia_lejana = (
        request.distancia_adicional_km >= THRESHOLDS["distancia_media_max_km"]
    )

    tiempo_bajo = (
        request.tiempo_estimado_min <= THRESHOLDS["tiempo_bajo_max_min"]
    )
    tiempo_medio = (
        THRESHOLDS["tiempo_bajo_max_min"]
        < request.tiempo_estimado_min
        < THRESHOLDS["tiempo_medio_max_min"]
    )
    tiempo_alto = (
        request.tiempo_estimado_min >= THRESHOLDS["tiempo_medio_max_min"]
    )

    una_parada = request.numero_supermercados == 1
    dos_paradas = request.numero_supermercados == 2
    compra_fragmentada = (
        request.numero_supermercados
        >= THRESHOLDS["compra_fragmentada_min_supermercados"]
    )

    return {
        "dentro_presupuesto": dentro_presupuesto,
        "presupuesto_ligeramente_excedido": presupuesto_ligeramente_excedido,
        "presupuesto_muy_excedido": presupuesto_muy_excedido,
        "todos_productos_disponibles": todos_productos_disponibles,
        "faltan_productos": not todos_productos_disponibles,
        "todos_esenciales_disponibles": todos_esenciales_disponibles,
        "faltan_esenciales": not todos_esenciales_disponibles,
        "ahorro_bajo": ahorro_bajo,
        "ahorro_medio": ahorro_medio,
        "ahorro_alto": ahorro_alto,
        "distancia_cercana": distancia_cercana,
        "distancia_media": distancia_media,
        "distancia_lejana": distancia_lejana,
        "tiempo_bajo": tiempo_bajo,
        "tiempo_medio": tiempo_medio,
        "tiempo_alto": tiempo_alto,
        "una_parada": una_parada,
        "dos_paradas": dos_paradas,
        "compra_fragmentada": compra_fragmentada,
        "promociones_relevantes": request.promociones_aplicables,
        "diferencia_presupuesto": diferencia_presupuesto,
        "porcentaje_exceso_presupuesto": porcentaje_exceso_presupuesto,
        "porcentaje_productos_disponibles": porcentaje_productos_disponibles,
        "porcentaje_esenciales_disponibles": porcentaje_esenciales_disponibles,
    }
