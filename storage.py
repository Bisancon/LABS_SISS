"""Временное хранилище прогнозов в оперативной памяти.

Интерфейс намеренно маленький: при переходе на SQLite/PostgreSQL
изменится только этот файл.
"""

from typing import Dict, List, Optional

_predictions: Dict[str, dict] = {}


def save(request_id: str, result: dict) -> None:
    _predictions[request_id] = result


def get(request_id: str) -> Optional[dict]:
    return _predictions.get(request_id)


def list_all(risk_level: Optional[str] = None, limit: int = 10) -> List[dict]:
    """Последние прогнозы (новые первыми) с фильтром по уровню риска."""
    items = list(_predictions.values())[::-1]
    if risk_level is not None:
        items = [i for i in items if i["risk_level"] == risk_level]
    return items[:limit]


def clear() -> None:
    _predictions.clear()
