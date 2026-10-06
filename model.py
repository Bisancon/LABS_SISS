"""«Модель»: метаданные и функция инференса.

Сейчас вместо обученной ML-модели используется простое правило.
Позже calculate_risk() можно заменить вызовом sklearn/PyTorch-модели,
не меняя ни API, ни схемы.
"""

import os

from schemas import FarmRequest

MODEL_NAME = "agro-risk-model"
MODEL_VERSION = "1.0"
MODEL_TYPE = "risk-scoring"


def is_ready() -> bool:
    """Имитация состояния модели.

    MODEL_READY=false в переменных окружения -> /predict вернёт 503.
    """
    return os.getenv("MODEL_READY", "true").lower() not in {"0", "false", "no"}


def calculate_risk(data: FarmRequest) -> float:
    """Оценка риска по финансовым и отраслевым показателям (0..1)."""
    score = 0.1

    if data.payment_delay_days > 30:   # длительная просрочка
        score += 0.3
    if data.previous_defaults > 0:     # были дефолты
        score += 0.3
    if data.debt > 5_000_000:          # большая задолженность
        score += 0.2
    if data.precipitation_mm < 100:    # засуха -> аграрный риск
        score += 0.1

    return round(min(score, 1.0), 2)
