"""Agro Scoring API: слой HTTP (маршруты, коды ответов, middleware)."""

import logging
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Request, status

import model
import services
import storage
from schemas import (
    FarmRequest,
    HealthResponse,
    ModelInfoResponse,
    PredictionResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(
    title="Agro Scoring API",
    description="REST API для оценки риска сельскохозяйственных предприятий.",
    version="1.0.0",
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """Добавляет заголовок X-Process-Time (секунды) к каждому ответу."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.perf_counter() - start, 6))
    return response


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка состояния API",
    description="Проверяет, что REST API запущен и отвечает.",
)
def health():
    return {"status": "ok"}


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Информация о модели",
    description="Название, версия, тип и текущее состояние модели.",
)
def model_info():
    return {
        "model_name": model.MODEL_NAME,
        "model_version": model.MODEL_VERSION,
        "model_type": model.MODEL_TYPE,
        "status": "ready" if model.is_ready() else "unavailable",
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Неизвестный регион"},
        503: {"description": "Модель временно недоступна"},
    },
    summary="Оценить риск хозяйства",
    description=(
        "Принимает характеристики хозяйства, выполняет валидацию, инференс "
        "и возвращает оценку риска. Результат сохраняется и доступен по request_id "
        "(поэтому 201 Created)."
    ),
)
def predict(request: FarmRequest):
    try:
        return services.make_prediction(request)
    except services.ModelUnavailableError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except services.UnknownRegionError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


# ВАЖНО: /predictions объявлен раньше /predictions/{request_id}
@app.get(
    "/predictions",
    response_model=List[PredictionResponse],
    responses={400: {"description": "Недопустимое значение risk_level"}},
    summary="Получить список прогнозов",
    description="Последние прогнозы (новые первыми). Фильтр по risk_level и лимит.",
)
def get_predictions(
    limit: int = Query(default=10, ge=1, le=100, description="Максимум результатов"),
    risk_level: Optional[str] = Query(default=None, description="low, medium или high"),
):
    if risk_level is not None and risk_level not in services.ALLOWED_LEVELS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="risk_level must be 'low', 'medium' or 'high'",
        )
    return storage.list_all(risk_level=risk_level, limit=limit)


@app.get(
    "/predictions/{request_id}",
    response_model=PredictionResponse,
    responses={404: {"description": "Прогноз с таким request_id не найден"}},
    summary="Получить прогноз по request_id",
    description="Возвращает сохранённый прогноз по его идентификатору.",
)
def get_prediction(request_id: str):
    result = storage.get(request_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
