"""Прогон тест-кейсов по живому серверу + скриншоты Swagger UI.
Сервер должен быть запущен на :8000 (и, для 503, на :8001 с MODEL_READY=false).
"""
import json
import subprocess
from html import escape
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000"

VALID = {"farm_id": "FARM-001", "region": "Krasnodar", "crop_type": "wheat", "area_ha": 2500,
         "temperature_avg": 24.3, "precipitation_mm": 320, "payment_delay_days": 45,
         "previous_defaults": 1, "debt": 6500000}
LOW = {**VALID, "farm_id": "FARM-002", "region": "Rostov", "payment_delay_days": 5,
       "previous_defaults": 0, "debt": 100000}
MEDIUM = {**VALID, "farm_id": "FARM-003", "region": "Stavropol", "previous_defaults": 0, "debt": 800000}
BAD_AREA = {**VALID, "farm_id": "FARM-1", "area_ha": -100}
BAD_REGION = {**VALID, "farm_id": "FARM-4", "region": "Moscow"}

# ---------- 1. тест-кейсы (реальные запросы) ----------
c = httpx.Client(base_url=BASE)
c.post("/predict", json=LOW); c.post("/predict", json=MEDIUM)
good = c.post("/predict", json=VALID)
rid = good.json()["request_id"]
cases = [
    ("GET /health", c.get("/health"), "200"),
    ("GET /model-info", c.get("/model-info"), "200"),
    ("корректный POST /predict", good, "200/201"),
    ("area_ha = -100", c.post("/predict", json=BAD_AREA), "422"),
    ("неизвестный регион", c.post("/predict", json=BAD_REGION), "400"),
    ("существующий request_id", c.get(f"/predictions/{rid}"), "200"),
    ("неизвестный request_id", c.get("/predictions/unknown-id"), "404"),
    ("limit = 2", c.get("/predictions", params={"limit": 2}), "200"),
    ("risk_level = high", c.get("/predictions", params={"risk_level": "high"}), "200"),
    ("limit = -5", c.get("/predictions", params={"limit": -5}), "422"),
]
rows = []
for i, (name, r, exp) in enumerate(cases, 1):
    ok = str(r.status_code) in exp.split("/")
    rows.append({"n": i, "case": name, "expected": exp, "got": r.status_code, "ok": ok})
json.dump(rows, open(OUT.parent / "test_cases.json", "w"), ensure_ascii=False, indent=1)
print(*[f'{r["n"]:>2} {r["case"]:<28} exp={r["expected"]:<7} got={r["got"]} {"PASS" if r["ok"] else "FAIL"}' for r in rows], sep="\n")

# ---------- 2. скриншоты Swagger UI ----------
def block_for(page, method, summary):
    return page.locator(f".opblock-{method}").filter(has_text=summary).first

def open_op(page, blk):
    if "is-open" not in (blk.get_attribute("class") or ""):
        blk.locator(".opblock-summary-control").first.click()
    if blk.locator(".try-out__btn.cancel").count() == 0:
        blk.locator(".try-out__btn").click()

def execute(page, blk, shot):
    blk.locator(".execute").click()
    blk.locator(".live-responses-table").wait_for(timeout=10000)
    page.wait_for_timeout(500)
    blk.scroll_into_view_if_needed()
    # снимаем блок только до конца «Server response» (без справочных примеров внизу)
    live = blk.locator(".live-responses-table")
    pg = blk.page
    sy = pg.evaluate("window.scrollY")
    b1, b2 = blk.bounding_box(), live.bounding_box()
    clip = {"x": b1["x"], "y": b1["y"] + sy, "width": b1["width"],
            "height": (b2["y"] + b2["height"]) - b1["y"] + 10}
    pg.screenshot(path=str(OUT / shot), clip=clip, full_page=True)

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=1.5)
    page.goto(BASE + "/docs"); page.wait_for_selector(".opblock")
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / "01_swagger_overview.png"), full_page=True)

    blk = block_for(page, "get", "Проверка состояния API"); open_op(page, blk); execute(page, blk, "02_health.png")
    blk = block_for(page, "get", "Информация о модели"); open_op(page, blk); execute(page, blk, "03_model_info.png")

    pred = block_for(page, "post", "Оценить риск хозяйства"); open_op(page, pred)
    for body, shot in [(VALID, "04_predict_ok.png"), (BAD_AREA, "05_predict_422.png"), (BAD_REGION, "06_predict_400.png")]:
        pred.locator("textarea.body-param__text").fill(json.dumps(body, indent=2, ensure_ascii=False))
        execute(page, pred, shot)

    # получение по id (подставляем реальный id)
    one = block_for(page, "get", "Получить прогноз по request_id"); open_op(page, one)
    inp = one.locator("tr[data-param-name='request_id'] input"); inp.fill(rid)
    execute(page, one, "07_get_by_id_200.png")
    inp.fill("unknown-id"); execute(page, one, "08_get_by_id_404.png")

    lst = block_for(page, "get", "Получить список прогнозов"); open_op(page, lst)
    lst.locator("tr[data-param-name='limit'] input").fill("2")
    execute(page, lst, "09_list_limit2.png")
    lst.locator("tr[data-param-name='limit'] input").fill("10")
    lst.locator("tr[data-param-name='risk_level'] input").fill("high")
    execute(page, lst, "10_list_high.png")
    lst.locator("tr[data-param-name='risk_level'] input").fill("")
    lst.locator("tr[data-param-name='limit'] input").fill("-5")
    execute(page, lst, "11_list_limit_422.png")

    # 503 на втором сервере (MODEL_READY=false)
    p2 = b.new_page(viewport={"width": 1200, "height": 900}, device_scale_factor=1.5)
    p2.goto("http://127.0.0.1:8001/docs"); p2.wait_for_selector(".opblock")
    pr2 = block_for(p2, "post", "Оценить риск хозяйства"); open_op(p2, pr2)
    pr2.locator("textarea.body-param__text").fill(json.dumps(VALID, indent=2))
    execute(p2, pr2, "12_predict_503.png")

    # терминальные «скриншоты»
    def term(title, text, name):
        html = f"""<body style='margin:0;background:#1e1e1e'><div style='padding:10px 16px;background:#333;color:#ddd;font:13px sans-serif'>{escape(title)}</div>
        <pre style='margin:0;padding:16px;color:#d4d4d4;font:13px/1.45 "DejaVu Sans Mono",monospace;width:1100px;white-space:pre-wrap'>{escape(text)}</pre></body>"""
        t = b.new_page(viewport={"width": 1132, "height": 200}, device_scale_factor=1.5)
        t.set_content(html); t.screenshot(path=str(OUT / name), full_page=True); t.close()

    root = Path(__file__).resolve().parent.parent
    tests = subprocess.run(["python", "-m", "pytest", "-v", "-p", "no:warnings"], cwd=root, capture_output=True, text=True).stdout
    term("$ python -m pytest -v", tests, "13_pytest.png")
    hdr = c.get("/health")
    term("$ curl -i http://127.0.0.1:8000/health",
         f"HTTP/1.1 {hdr.status_code} OK\n" + "\n".join(f"{k}: {v}" for k, v in hdr.headers.items()) + "\n\n" + hdr.text,
         "14_curl_health_headers.png")
    b.close()
print("screenshots:", sorted(x.name for x in OUT.glob("*.png")))
