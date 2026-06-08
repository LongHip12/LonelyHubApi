import os
import json
import time
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOKS = {
    "mirage": "https://discord.com/api/webhooks/1513404305325953055/tbj3rwOS_51utpyqnlSMTQATkA2iY2xlOSc3ZfnngqpGrFmyBl2e8yWhtVs9KO996dNq",
    "prehistoric": "https://discord.com/api/webhooks/1513404845024083998/8XYS6f5qT2DtEhKVUx46LC2tGhTOQwgk3kCsvNLnVBoDTkK6P9-FcnHw7QflO3NBiIpD",
    "kitsune": "https://discord.com/api/webhooks/1513405002138386432/ok5BqNmL5ppcQJLTfbwjrH52FcsUdYFuiVro83YeCfWnU-Jwi4zpgcXXVYPsl_vR8OHL",
    "fullmoon": "https://discord.com/api/webhooks/1513405097747546182/jtrsHlyZmrwofPPiMplTzgwgWYcW5cSjfEZfTA4nMenyxh92mBxaIGejPP7GQmx1x6K_",
    "nearmoon": "https://discord.com/api/webhooks/1513405176466116711/YRDfrcRky6nyZPpaABXDt-RUDxR0itaWKAoCmAjSCyAsXrMgL61lRyFsVhlW1Laj42dV",
    "ripindra": "https://discord.com/api/webhooks/1513405295676756038/DpRkeOhzq7UfKE0JiLFzpzVGJZTZF_DpnhAi_Nv0abEwrUN4I9kK_DG4dZiBAB-bOoOC",
    "doughking": "https://discord.com/api/webhooks/1513405365545472070/_Cqy7jwKBr9DwCBum8mu7UEf3P-2Biq4aXwfCGSSAZCDspDljY60TJSa8BpXfLQknXWx",
    "katakuri": "https://discord.com/api/webhooks/1513405454577959083/YdDrA5o4_kSSJD3ALoG0gmafphsokXoo4VdSK4c28UTU8ZBjVOK1waTEBzoIQnbtY6hs",
    "tyrant": "https://discord.com/api/webhooks/1513405533858697277/pbaTKeGDhVFsTIneeLpMojloFRHYyDagI4EtQ1AX-79pEgLstUgfNtRlk55NOaXlZZR-",
    "darkbeard": "https://discord.com/api/webhooks/1513405620789710878/YCeG3r2Bwv_i_3vvKFsYUgZ_rr4FomFiCSB3oaco0_i4CitD6JCGV91ymBht--ig6dge",
    "soulreaper": "https://discord.com/api/webhooks/1513405697692401705/sasrbmrq03Fy8KQn19iWccGu1Wwpegf5d5KrFGiNNm4Rbw9Qrl5jMWsG_zprNwmdqpuq",
    "cursedcaptain": "https://discord.com/api/webhooks/1513405788360806480/6Jzv4Ywvc7YIF8vOsL73hqQ5CZfnMEyB32eDwHr8v9flCz8vn-vrH3Ozy5htt3HrppL9",
    "swordlegendary": "https://discord.com/api/webhooks/1513405894208127016/tOL0AyzKhN3Ef3B5dTQF3OV9mkxmUSQDbjzoY8S0fO0Um-b_FWRuClkCI7AtLERk9oxZ",
    "hakilegendary": "https://discord.com/api/webhooks/1513405968405368982/GHyo--6s8dZadjw-hVOJzpCGxWsdmAWamzLvW9pmH1LmxH7jnRaZxQPaJKJqVph6XLts",
}

EXECUTE_WEBHOOK = "https://discord.com/api/webhooks/1513412624979591230/WxEwthKabsfJmqVYfGJCJ2S69rKPmXhIbxs-nlk0rEbP2GiV1F6fTXgIOBtFhmLoL2vG"

BLOCKED_V2 = ["@everyone", "@here", "spam", "spammed", "raidded", "@"]
BLOCKED_V3 = ["@everyone", "@here"]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

rate_buckets = {}
rate_lock = threading.Lock()


def check_rate_limit(key, max_per_minute):
    now = time.time()
    with rate_lock:
        bucket = rate_buckets.get(key)
        if not bucket or now >= bucket["reset_at"]:
            rate_buckets[key] = {"count": 1, "reset_at": now + 60}
            return True
        if bucket["count"] >= max_per_minute:
            return False
        bucket["count"] += 1
        return True


def read_json(name, default):
    path = os.path.join(DATA_DIR, f"{name}.json")
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def write_json(name, data):
    path = os.path.join(DATA_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f)


def get_execute_count():
    return read_json("executeCount", 31957)


def increment_execute_count():
    c = get_execute_count() + 1
    write_json("executeCount", c)
    return c


def get_ip(req):
    forwarded = req.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return req.remote_addr or "unknown"


def contains_blocked(data, blocked_list):
    text = json.dumps(data).lower()
    return any(b.lower() in text for b in blocked_list)


@app.route("/api/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/api/v2/send/<name>", methods=["POST"])
def v2_send(name):
    webhook = WEBHOOKS.get(name.lower())
    if not webhook:
        return jsonify({"error": "Unknown endpoint"}), 404

    ip = get_ip(request)
    if not check_rate_limit(f"v2:{name}:{ip}", 30):
        return jsonify({"error": "Rate limit exceeded. Max 30 requests per minute."}), 429

    body = request.get_json(silent=True) or {}
    embeds = body.get("embeds")
    if not embeds or not isinstance(embeds, list) or len(embeds) == 0:
        return jsonify({"error": "Only embeds are allowed."}), 400

    if contains_blocked(body, BLOCKED_V2):
        return jsonify({"error": "Payload contains forbidden content."}), 403

    r = requests.post(webhook, json={"embeds": embeds}, timeout=10)
    if not r.ok:
        return jsonify({"error": "Discord error", "detail": r.text}), r.status_code

    return jsonify({"success": True, "message": "Sent to Discord."})


@app.route("/api/v1/bloxfruit/<name>", methods=["POST"])
def v1_bloxfruit(name):
    webhook = WEBHOOKS.get(name.lower())
    if not webhook:
        return jsonify({"error": "Unknown endpoint"}), 404

    ip = get_ip(request)
    if not check_rate_limit(f"v1:{name}:{ip}", 30):
        return jsonify({"error": "Rate limit exceeded. Max 30 requests per minute."}), 429

    body = request.get_json(silent=True) or {}
    embeds = body.get("embeds")
    if not embeds or not isinstance(embeds, list) or len(embeds) == 0:
        return jsonify({"error": "Only embeds are allowed."}), 400

    if contains_blocked(body, BLOCKED_V2):
        return jsonify({"error": "Payload contains forbidden content."}), 403

    r = requests.post(webhook, json={"embeds": embeds}, timeout=10)
    if not r.ok:
        return jsonify({"error": "Discord error", "detail": r.text}), r.status_code

    return jsonify({"success": True, "message": "Sent to Discord."})


@app.route("/api/v5/oauth2/execute", methods=["POST"])
def v5_execute():
    body = request.get_json(silent=True) or {}
    required = ["DisplayName", "Username", "UserID", "Executor", "HWID", "PlaceID", "JobID", "ScriptJoin"]
    missing = [k for k in required if not body.get(k) and body.get(k) != 0]
    if missing:
        return jsonify({"error": "Missing required fields", "missing": missing}), 400

    total = increment_execute_count()

    display_name = str(body["DisplayName"])
    username = str(body["Username"])
    user_id = str(body["UserID"])
    executor = str(body["Executor"])
    hwid = str(body["HWID"])
    place_id = str(body["PlaceID"])
    job_id = str(body["JobID"])

    payload = {
        "username": "Lonely Hub",
        "avatar_url": "https://i.imgur.com/xY7M2iE.jpeg",
        "embeds": [{
            "title": "Roblox Account Information",
            "url": f"https://www.roblox.com/users/{user_id}",
            "description": f"Display Name: **{display_name}**",
            "color": 0x00FFFF,
            "thumbnail": {"url": f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"},
            "fields": [
                {"name": "[👤] User Name", "value": f"```\n{username}\n```", "inline": True},
                {"name": "[🆔] User ID", "value": f"```\n{user_id}\n```", "inline": True},
                {"name": "[🖥️] Executor", "value": f"```\n{executor}\n```", "inline": True},
                {"name": "[🧬] HWID", "value": f"```\n{hwid}\n```", "inline": True},
                {"name": "[🌏] Place ID", "value": f"```\n{place_id}\n```", "inline": True},
                {"name": "[🔗] Job ID", "value": f"```\n{job_id}\n```", "inline": True},
                {"name": "[📜] Script Join", "value": f'```lua\ngame:GetService("TeleportService"):TeleportToPlaceInstance({place_id}, "{job_id}", game.Players.LocalPlayer)```', "inline": False},
                {"name": "[🎮] Type Script", "value": "```\nMain Silent Assassins\n```", "inline": False},
                {"name": "[🚀] Total Execute", "value": f"```\n{total}\n```", "inline": False},
            ]
        }]
    }

    r = requests.post(EXECUTE_WEBHOOK, json=payload, timeout=10)
    if not r.ok:
        return jsonify({"error": "Discord error", "detail": r.text}), r.status_code

    return jsonify({"success": True, "totalExecute": total})


@app.route("/api/v5/services/lonelyhub", methods=["GET"])
@app.route("/api/v5/services/lonelyhub/", methods=["GET"])
def v5_lonelyhub():
    return jsonify({"Name": "Lonely Hub", "Total Execute": get_execute_count()})


@app.route("/api/v3/apis", methods=["POST"])
def v3_create():
    body = request.get_json(silent=True) or {}
    api_id = str(body.get("apiId", "")).strip()
    api_name = str(body.get("apiName", "")).strip()
    webhook = str(body.get("webhook", "")).strip()
    rate_limit = int(body.get("rateLimit", 30))

    if not api_id or not api_name or not webhook:
        return jsonify({"error": "apiId, apiName, and webhook are required."}), 400

    reg = read_json("apiRegistry", {})
    reg[api_id] = {"apiId": api_id, "apiName": api_name, "webhook": webhook, "rateLimit": rate_limit}
    write_json("apiRegistry", reg)

    return jsonify({"success": True, "apiId": api_id, "apiName": api_name, "endpoint": f"/api/v3/{api_id}/send/{api_name}"}), 201


@app.route("/api/v3/apis/<api_id>", methods=["PUT"])
def v3_edit(api_id):
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry:
        return jsonify({"error": "API not found."}), 404

    body = request.get_json(silent=True) or {}
    entry["apiName"] = str(body.get("apiName", entry["apiName"])).strip()
    entry["webhook"] = str(body.get("webhook", entry["webhook"])).strip()
    entry["rateLimit"] = int(body.get("rateLimit", entry["rateLimit"]))
    reg[api_id] = entry
    write_json("apiRegistry", reg)

    return jsonify({"success": True, "apiId": api_id, "apiName": entry["apiName"], "endpoint": f"/api/v3/{api_id}/send/{entry['apiName']}"})


@app.route("/api/v3/<api_id>/send/<api_name>", methods=["POST"])
def v3_send(api_id, api_name):
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry or entry["apiName"].lower() != api_name.lower():
        return jsonify({"error": "API not found."}), 404

    ip = get_ip(request)
    if not check_rate_limit(f"v3:{api_id}:{ip}", entry["rateLimit"]):
        return jsonify({"error": f"Rate limit exceeded. Max {entry['rateLimit']} requests per minute."}), 429

    body = request.get_json(silent=True) or {}
    if contains_blocked(body, BLOCKED_V3):
        return jsonify({"error": "Payload contains forbidden content."}), 403

    header_lines = "\n".join(f"    + {k}: {v}" for k, v in body.items())
    content = f"# API Post Detected!\n- **API Name**: {entry['apiName']}\n- **API ID**: {api_id}\n- **Headers**:\n{header_lines}"

    r = requests.post(entry["webhook"], json={"content": content}, timeout=10)
    if not r.ok:
        return jsonify({"error": "Discord error", "detail": r.text}), r.status_code

    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
