"""
Сервер управления роботизированной клешнёй на пневматической мышце Маккиббена.

Клешня из двух пальцев сжимается за счёт пневмомышцы: компрессор нагнетает в неё
воздух, мышца раздувается в диаметре и укорачивается, через сухожилия сводя
пальцы клешни. Чем выше давление — тем сильнее сжата клешня.

Состояние (целевое давление, сжата ли клешня) хранится ЗДЕСЬ, на сервере,
а не в браузере. Кнопки и ползунок на странице шлют запросы сюда, сервер их
обрабатывает, меняет состояние и возвращает его обратно.

В реальном изделии тот же обмен ведёт контроллер ESP32: он принимает запросы
и управляет клапаном/компрессором (например, ШИМ-сигналом на электроклапан),
регулируя давление в мышце.

Запуск:
    pip install flask
    python server.py
Затем открыть в браузере http://127.0.0.1:5000
"""

from flask import Flask, jsonify, request, send_from_directory
import os

app = Flask(__name__)

# ── Параметры пневмосистемы ──
PRESSURE_MIN = 0     # давление при расслабленной мышце (клешня раскрыта), %
PRESSURE_MAX = 100   # максимальное давление (клешня полностью сжата), %
GRIP_THRESHOLD = 60  # с какого давления считаем, что клешня уверенно сжала предмет

# ── Состояние живёт на сервере ──
state = {
    "pressure": 0,      # текущее целевое давление в мышце, %
    "closed": False,    # сжата ли клешня
}


def make_status():
    """Собрать текущий статус для отправки клиенту."""
    p = state["pressure"]
    if p <= 3:
        st = "раскрыта"
    elif p >= GRIP_THRESHOLD:
        st = "сжата"
    else:
        st = "сжимается"
    return {
        "pressure": p,
        "closed": state["closed"],
        "state": st,
    }


# ── Раздача страницы ──
@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")


# ── Команды управления (обрабатываются на сервере) ──
@app.route("/close", methods=["POST", "GET"])
def close_claw():
    """Сжать клешню — накачать мышцу (полное давление)."""
    state["pressure"] = PRESSURE_MAX
    state["closed"] = True
    return jsonify(make_status())


@app.route("/open", methods=["POST", "GET"])
def open_claw():
    """Разжать клешню — стравить воздух."""
    state["pressure"] = PRESSURE_MIN
    state["closed"] = False
    return jsonify(make_status())


@app.route("/pressure", methods=["POST", "GET"])
def set_pressure():
    """Установить произвольное давление в мышце (регулировка силы сжатия)."""
    try:
        p = int(request.args.get("value", state["pressure"]))
    except (TypeError, ValueError):
        return jsonify({"error": "bad value"}), 400
    p = max(PRESSURE_MIN, min(PRESSURE_MAX, p))
    state["pressure"] = p
    state["closed"] = p >= GRIP_THRESHOLD
    return jsonify(make_status())


@app.route("/status")
def status():
    """Отдать текущее состояние (панель опрашивает его автоматически)."""
    return jsonify(make_status())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
