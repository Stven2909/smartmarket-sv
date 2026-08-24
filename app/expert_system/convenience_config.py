from dataclasses import dataclass
from math import isclose

CONVENIENCE_CONFIG_VERSION = "1.0.0"


@dataclass(frozen=True)
class ConvenienceConfig:
    """Configuración explícita y validada del índice auxiliar."""

    ahorro_referencia: float = 20.0
    distancia_maxima: float = 20.0
    tiempo_maximo: float = 120.0
    peso_ahorro: float = 0.35
    peso_disponibilidad: float = 0.25
    peso_distancia: float = 0.20
    peso_tiempo: float = 0.15
    peso_promociones: float = 0.05

    def __post_init__(self) -> None:
        weights = (
            self.peso_ahorro,
            self.peso_disponibilidad,
            self.peso_distancia,
            self.peso_tiempo,
            self.peso_promociones,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("Todos los pesos deben ser mayores o iguales que cero")
        if not isclose(sum(weights), 1.0, abs_tol=1e-9):
            raise ValueError("La suma de los pesos debe ser igual a 1")

        limits = (
            self.ahorro_referencia,
            self.distancia_maxima,
            self.tiempo_maximo,
        )
        if any(limit <= 0 for limit in limits):
            raise ValueError("Los límites de normalización deben ser positivos")

    def weights(self) -> dict[str, float]:
        return {
            "ahorro": self.peso_ahorro,
            "disponibilidad": self.peso_disponibilidad,
            "distancia": self.peso_distancia,
            "tiempo": self.peso_tiempo,
            "promociones": self.peso_promociones,
        }


DEFAULT_CONVENIENCE_CONFIG = ConvenienceConfig()
