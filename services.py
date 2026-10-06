"""Бизнес-логика: валидация, постпроцессинг, оркестрация инференса."""

import logging
import uuid

import model
import storage
from schemas import FarmRequest

logger = logging.getLogger(__name__)

ALLOWED_REGIONS = {"Krasnodar", "Rostov", "Stavropol"}
ALLOWED_LEVELS = {"low", "medium", "high"}


class ModelUnavailableError(Exception):
    """Модель не готова к инференсу (-> HTTP 503)."""


class UnknownRegionError(ValueError):
    """Регион не входит в справочник (-> HTTP 400)."""


def get_risk_level(score: float) -> str:
    if score < 0.3:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def get_recommendation(level: str) -> str:
    if level == "low":
        return "Стандартное рассмотрение"
    if level == "medium":
        return "Требуется дополнительная проверка"
    return "Высокий риск. Требуется ручное рассмотрение"


def validate_region(region: str) -> None:
    if region not in ALLOWED_REGIONS:
        raise UnknownRegionError(
            f"Unknown region: {region}. Allowed regions: {sorted(ALLOWED_REGIONS)}"
        )


def make_prediction(data: FarmRequest) -> dict:
    """Полный контур: проверки -> инференс -> постпроцессинг -> сохранение."""
    if not model.is_ready():
        raise ModelUnavailableError("Model is temporarily unavailable")

    validate_region(data.region)

    logger.info("Prediction request received | farm_id=%s", data.farm_id)

    score = model.calculate_risk(data)
    level = get_risk_level(score)

    result = {
        "request_id": str(uuid.uuid4()),
        "farm_id": data.farm_id,
        "risk_score": score,
        "risk_level": level,
        "recommendation": get_recommendation(level),
        "model_version": model.MODEL_VERSION,
    }
    storage.save(result["request_id"], result)

    logger.info(
        "Prediction completed | request_id=%s | farm_id=%s | risk_score=%s | risk_level=%s",
        result["request_id"], data.farm_id, score, level,
    )
    return result
