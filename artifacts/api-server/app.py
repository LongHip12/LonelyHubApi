import os
import json
import time
import threading
import hashlib
import functools
import uuid
import requests
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__, static_url_path='/api/static')
app.secret_key = os.environ.get("SESSION_SECRET", "lonelyhub-secret-2024")

_wh_raw = os.environ.get("WEBHOOKS_JSON", "{}")
try:
    _wh_data = json.loads(_wh_raw)
except Exception:
    _wh_data = {}

WEBHOOKS = {k: v for k, v in _wh_data.items() if k != "__execute__"}
EXECUTE_WEBHOOK = _wh_data.get("__execute__", "")
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


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_users():
    return read_json("users", {})


def save_users(users):
    write_json("users", users)


def get_user_by_username(username):
    for uid, user in get_users().items():
        if user["username"].lower() == username.lower():
            return user
    return None


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return get_users().get(uid)


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        if user["role"] != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


def page_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            return redirect("/api/admin/login")
        return f(*args, **kwargs)
    return decorated


@app.route("/api/healthz")
def healthz():
    return {"status": "ok"}


@app.route("/api/admin/login")
def admin_login_page():
    user = get_current_user()
    if user:
        return redirect("/admin")
    return render_template("login.html")


@app.route("/admin")
@page_required
def admin_page():
    user = get_current_user()
    if user["role"] not in ("admin", "manager"):
        return redirect("/api/admin/login")
    return render_template("admin.html", username=user["username"], role=user["role"])


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = get_user_by_username(username)
    if not user or user["password"] != hash_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    if username.lower() == "longhip12" and user["role"] != "admin":
        users = get_users()
        users[user["id"]]["role"] = "admin"
        save_users(users)
        user = users[user["id"]]

    session["user_id"] = user["id"]
    return jsonify({"success": True, "user": {"id": user["id"], "username": user["username"], "role": user["role"]}})


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    body = request.get_json(silent=True) or {}
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", ""))
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if get_user_by_username(username):
        return jsonify({"error": "Username already exists"}), 409

    uid = str(uuid.uuid4())
    role = "admin" if username.lower() == "longhip12" else "member"
    users = get_users()
    users[uid] = {
        "id": uid,
        "username": username,
        "password": hash_password(password),
        "role": role,
        "created_at": int(time.time()),
    }
    save_users(users)
    session["user_id"] = uid
    return jsonify({"success": True, "user": {"id": uid, "username": username, "role": role}}), 201


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/me")
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"id": user["id"], "username": user["username"], "role": user["role"]})


@app.route("/api/admin/users")
@admin_required
def admin_list_users():
    users = get_users()
    result = [{"id": u["id"], "username": u["username"], "role": u["role"], "created_at": u.get("created_at", 0)} for u in users.values()]
    return jsonify(result)


@app.route("/api/admin/users/<uid>/role", methods=["PUT"])
@admin_required
def admin_set_role(uid):
    body = request.get_json(silent=True) or {}
    role = str(body.get("role", "")).strip()
    if role not in ("member", "manager", "admin"):
        return jsonify({"error": "Invalid role"}), 400
    users = get_users()
    if uid not in users:
        return jsonify({"error": "User not found"}), 404
    users[uid]["role"] = role
    save_users(users)
    return jsonify({"success": True})


@app.route("/api/admin/users/<uid>", methods=["DELETE"])
@admin_required
def admin_delete_user(uid):
    users = get_users()
    if uid not in users:
        return jsonify({"error": "User not found"}), 404
    del users[uid]
    save_users(users)
    return jsonify({"success": True})


@app.route("/api/admin/apis")
@login_required
def admin_list_apis():
    user = get_current_user()
    reg = read_json("apiRegistry", {})
    if user["role"] == "admin":
        apis = list(reg.values())
    else:
        apis = [a for a in reg.values() if a.get("owner", "").lower() == user["username"].lower()]
    return jsonify(apis)


@app.route("/api/admin/apis/<api_id>", methods=["PUT"])
@login_required
def admin_edit_api(api_id):
    user = get_current_user()
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    if user["role"] != "admin" and entry.get("owner", "").lower() != user["username"].lower():
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    entry["apiName"] = str(body.get("apiName", entry["apiName"])).strip()
    entry["webhook"] = str(body.get("webhook", entry.get("webhook", ""))).strip()
    entry["rateLimit"] = int(body.get("rateLimit", entry.get("rateLimit", 30)))
    if "defaultValue" in body:
        entry["defaultValue"] = body["defaultValue"]
    if "source" in body:
        entry["source"] = str(body["source"]).strip()
    reg[api_id] = entry
    write_json("apiRegistry", reg)
    return jsonify({"success": True})


@app.route("/api/admin/apis/<api_id>", methods=["DELETE"])
@login_required
def admin_delete_api(api_id):
    user = get_current_user()
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    if user["role"] != "admin" and entry.get("owner", "").lower() != user["username"].lower():
        return jsonify({"error": "Forbidden"}), 403
    del reg[api_id]
    write_json("apiRegistry", reg)
    return jsonify({"success": True})


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
    user = get_current_user()
    body = request.get_json(silent=True) or {}
    api_id = str(body.get("apiId", "")).strip()
    api_name = str(body.get("apiName", "")).strip()
    webhook = str(body.get("webhook", "")).strip()
    rate_limit = int(body.get("rateLimit", 30))
    default_value = body.get("defaultValue", None)
    owner = user["username"].lower() if user else str(body.get("owner", "")).strip().lower()
    source = str(body.get("source", "")).strip()

    if not api_id or not api_name:
        return jsonify({"error": "apiId and apiName are required."}), 400

    reg = read_json("apiRegistry", {})
    reg[api_id] = {
        "apiId": api_id,
        "apiName": api_name,
        "webhook": webhook,
        "rateLimit": rate_limit,
        "owner": owner,
        "source": source,
        "defaultValue": default_value,
        "total": 0,
    }
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
    entry["webhook"] = str(body.get("webhook", entry.get("webhook", ""))).strip()
    entry["rateLimit"] = int(body.get("rateLimit", entry.get("rateLimit", 30)))
    if "defaultValue" in body:
        entry["defaultValue"] = body["defaultValue"]
    if "source" in body:
        entry["source"] = str(body["source"]).strip()
    reg[api_id] = entry
    write_json("apiRegistry", reg)
    return jsonify({"success": True, "apiId": api_id, "apiName": entry["apiName"], "endpoint": f"/api/v3/{api_id}/send/{entry['apiName']}"})


@app.route("/api/v3/<api_id>/get/<api_name>", methods=["GET"])
def v3_get(api_id, api_name):
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry or entry["apiName"].lower() != api_name.lower():
        return jsonify({"error": "API not found"}), 404
    default_value = entry.get("defaultValue")
    data = [default_value] if default_value is not None else []
    return jsonify({
        "success": True,
        "id": api_id,
        "name": entry["apiName"],
        "owner": entry.get("owner", ""),
        "source": entry.get("source", ""),
        "data": data,
        "total": str(entry.get("total", 0)),
    })


@app.route("/api/v3/<api_id>/send/<api_name>", methods=["POST"])
def v3_send(api_id, api_name):
    reg = read_json("apiRegistry", {})
    entry = reg.get(api_id)
    if not entry or entry["apiName"].lower() != api_name.lower():
        return jsonify({"error": "API not found."}), 404
    ip = get_ip(request)
    if not check_rate_limit(f"v3:{api_id}:{ip}", entry.get("rateLimit", 30)):
        return jsonify({"error": f"Rate limit exceeded. Max {entry.get('rateLimit', 30)} requests per minute."}), 429
    body = request.get_json(silent=True) or {}
    if contains_blocked(body, BLOCKED_V3):
        return jsonify({"error": "Payload contains forbidden content."}), 403

    entry["total"] = entry.get("total", 0) + 1
    reg[api_id] = entry
    write_json("apiRegistry", reg)

    webhook = entry.get("webhook", "")
    if webhook:
        header_lines = "\n".join(f"    + {k}: {v}" for k, v in body.items())
        content = f"# API Post Detected!\n- **API Name**: {entry['apiName']}\n- **API ID**: {api_id}\n- **Headers**:\n{header_lines}"
        try:
            requests.post(webhook, json={"content": content}, timeout=10)
        except Exception:
            pass

    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
