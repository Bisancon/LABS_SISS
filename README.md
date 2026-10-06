# Agro Scoring API

REST API для оценки риска сельскохозяйственных предприятий (FastAPI).
Лабораторная работа №1 «Проектирование AI-сервиса на FastAPI».

## Структура

| Файл | Назначение |
|---|---|
| `main.py` | HTTP-слой: маршруты, коды ответов, middleware |
| `schemas.py` | Pydantic-схемы (контракт API) |
| `model.py` | «Модель»: метаданные и `calculate_risk()` |
| `services.py` | Бизнес-логика: валидация региона, постпроцессинг, оркестрация |
| `storage.py` | Хранилище прогнозов (in-memory) |
| `tests/` | pytest-тесты всех эндпоинтов |
| `scripts/` | прогон тест-кейсов и снятие скриншотов |

## Запуск

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

uvicorn main:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs · OpenAPI: http://127.0.0.1:8000/openapi.json

## Тесты

```bash
python -m pytest -v
```

## Проверка 503

```bash
$env:MODEL_READY="false"; uvicorn main:app --reload
```
