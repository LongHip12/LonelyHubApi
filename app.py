from flask import Flask, request, jsonify
from collections import deque
from dotenv import load_dotenv
import os
import time
import requests as req_lib

load_dotenv()

app = Flask(__name__)

BLOXFRUIT_ENDPOINTS = [
    "mirage", "prehistoric", "fullmoon", "nearmoon",
    "sword", "haki", "doughking", "katakuri",
    "indra", "soulreaper", "elite", "darkbeard",
    "cursedcaptain", "tyrant", "kitsune"
]

WEBHOOK_MAP = {}
for ep in BLOXFRUIT_ENDPOINTS:
    url = os.getenv(f"WEBHOOK_{ep.upper()}")
    if url:
        WEBHOOK_MAP[ep] = url
    else:
        print(f"[Warning] No env var found for WEBHOOK_{ep.upper()}")

BANNED_WORDS = ["@here", "@everyone"]

storage = {ep: [] for ep in BLOXFRUIT_ENDPOINTS}

rate_limit_log = deque()
RATE_LIMIT = 30
RATE_WINDOW = 60


def check_rate_limit():
    now = time.time()
    while rate_limit_log and now - rate_limit_log[0] > RATE_WINDOW:
        rate_limit_log.popleft()
    if len(rate_limit_log) >= RATE_LIMIT:
        return False
    rate_limit_log.append(now)
    return True


def contains_banned_words(obj):
    if isinstance(obj, str):
        for word in BANNED_WORDS:
            if word in obj:
                return True
    elif isinstance(obj, dict):
        for v in obj.values():
            if contains_banned_words(v):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if contains_banned_words(item):
                return True
    return False


VALID_ITEM_KEYS = {"Name", "Players", "JobId", "World"}


def validate_item(item):
    if not isinstance(item, dict):
        return False, "Each item in data must be an object"
    if set(item.keys()) != VALID_ITEM_KEYS:
        return False, f"Each item must have exactly these keys: {VALID_ITEM_KEYS}"
    if not isinstance(item.get("Name"), str):
        return False, "Name must be a string"
    if not isinstance(item.get("Players"), int):
        return False, "Players must be an integer"
    if not isinstance(item.get("JobId"), str):
        return False, "JobId must be a string"
    if not isinstance(item.get("World"), int):
        return False, "World must be an integer"
    return True, None


def make_v1_endpoint(endpoint_name):
    def handler():
        if request.method == "GET":
            entries = storage[endpoint_name]
            return jsonify({
                "source": "python 3.15",
                "success": True,
                "total": len(entries),
                "data": entries
            })

        body = request.get_json(silent=True)
        if body is None:
            return jsonify({"source": "python 3.15", "success": False, "error": "Invalid or missing JSON body"}), 400

        data = body.get("data")
        if not isinstance(data, list):
            return jsonify({"source": "python 3.15", "success": False, "error": "Field 'data' must be an array"}), 400

        for i, item in enumerate(data):
            ok, err = validate_item(item)
            if not ok:
                return jsonify({"source": "python 3.15", "success": False, "error": f"Item [{i}]: {err}"}), 400

        storage[endpoint_name] = data
        return jsonify({
            "source": "python 3.15",
            "success": True,
            "total": len(data),
            "data": data
        })

    handler.__name__ = f"bloxfruit_v1_{endpoint_name}"
    return handler


def make_v2_endpoint(endpoint_name):
    def handler():
        if not check_rate_limit():
            print(f"[Warning] Rate limit exceeded on /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": "Rate limit exceeded: max 30 requests per minute"}), 429

        body = request.get_json(silent=True)
        if body is None:
            print(f"[Error] Invalid JSON body on /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": "Invalid or missing JSON body"}), 400

        embeds = body.get("embeds")
        if not embeds or not isinstance(embeds, list) or len(embeds) == 0:
            print(f"[Warning] Non-embed payload rejected on /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": "Only embed payloads are accepted. Send {'embeds': [...]}"}), 400

        for key in body:
            if key not in ("embeds", "username", "avatar_url"):
                print(f"[Warning] Extra field '{key}' rejected on /api/v2/send/{endpoint_name}")
                return jsonify({"source": "python 3.15", "success": False, "error": f"Only embeds are allowed. Field '{key}' is not permitted"}), 400

        if contains_banned_words(embeds):
            print(f"[Warning] Banned word detected in embed on /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": "Embed contains banned words (@here, @everyone)"}), 400

        webhook_url = WEBHOOK_MAP.get(endpoint_name)
        if not webhook_url:
            print(f"[Warning] No webhook configured for endpoint: {endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": "No webhook configured for this endpoint"}), 404

        payload = {"embeds": embeds}
        if "username" in body:
            payload["username"] = body["username"]
        if "avatar_url" in body:
            payload["avatar_url"] = body["avatar_url"]

        resp = req_lib.post(webhook_url, json=payload, timeout=10)

        if resp.status_code in (200, 204):
            print(f"[Info] Webhook sent successfully for /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": True, "message": "Webhook sent"})
        else:
            print(f"[Error] Discord webhook error {resp.status_code} for /api/v2/send/{endpoint_name}")
            return jsonify({"source": "python 3.15", "success": False, "error": f"Discord returned {resp.status_code}", "detail": resp.text}), 502

    handler.__name__ = f"bloxfruit_v2_{endpoint_name}"
    return handler


@app.route("/")
def index():
    return "Api By LongHip12"


for ep in BLOXFRUIT_ENDPOINTS:
    app.add_url_rule(
        f"/api/v1/bloxfruit/{ep}",
        view_func=make_v1_endpoint(ep),
        methods=["GET", "POST"]
    )
    app.add_url_rule(
        f"/api/v2/send/{ep}",
        view_func=make_v2_endpoint(ep),
        methods=["POST"]
    )


if __name__ == "__main__":
    app.run(debug=True)
