"""Pydantic-схемы: контракт между клиентами и API."""

from pydantic import BaseModel, Field


class FarmRequest(BaseModel):
    """Данные хозяйства, которые клиент передаёт в POST /predict."""

    farm_id: str = Field(..., min_length=1, description="Идентификатор хозяйства")
    region: str = Field(..., min_length=1, description="Регион хозяйства")
    crop_type: str = Field(..., min_length=1, description="Основная сельскохозяйственная культура")
    area_ha: float = Field(..., gt=0, description="Площадь посевов, га")
    temperature_avg: float = Field(..., ge=-60, le=60, description="Средняя температура, °C")
    precipitation_mm: float = Field(..., ge=0, description="Количество осадков, мм")
    payment_delay_days: int = Field(..., ge=0, description="Количество дней просрочки платежа")
    previous_defaults: int = Field(..., ge=0, description="Количество предыдущих дефолтов")
    debt: float = Field(..., ge=0, description="Текущая задолженность")

    model_config = {
        "json_schema_extra": {
            "example": {
                "farm_id": "FARM-001",
                "region": "Krasnodar",
                "crop_type": "wheat",
                "area_ha": 2500,
                "temperature_avg": 24.3,
                "precipitation_mm": 320,
                "payment_delay_days": 45,
                "previous_defaults": 1,
                "debt": 6500000,
            }
        }
    }


class PredictionResponse(BaseModel):
    """Ответ сервиса после выполнения прогноза."""

    request_id: str
    farm_id: str
    risk_score: float
    risk_level: str
    recommendation: str
    model_version: str


class HealthResponse(BaseModel):
    status: str


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    status: str
