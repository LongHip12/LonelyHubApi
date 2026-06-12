import os
import json
import time
import math
import threading
import hashlib
import functools
import uuid
import requests
from flask import Flask, request, jsonify, session, send_from_directory

app = Flask(__name__, static_folder=None)
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
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
os.makedirs(DATA_DIR, exist_ok=True)

rate_buckets = {}
rate_lock = threading.Lock()
PAGE_SIZE = 10


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


def is_admin(user):
    return user and (user.get("role") == "admin" or user.get("username", "").lower() == "longhip12")


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
        if not is_admin(user):
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


def get_registry():
    return read_json("apiRegistry2", {})


def save_registry(reg):
    write_json("apiRegistry2", reg)


def user_to_public(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "isAdmin": is_admin(user),
        "createdAt": user.get("created_at", 0) * 1000,
    }


def api_to_public(entry, include_data=True):
    obj = {
        "id": entry["id"],
        "apiId": entry["apiId"],
        "apiName": entry["apiName"],
        "displayName": entry.get("displayName", entry["apiName"]),
        "webhookUrl": entry.get("webhookUrl", ""),
        "visibility": entry.get("visibility", "Public"),
        "whitelistIps": entry.get("whitelistIps", []),
        "rateLimit": entry.get("rateLimit"),
        "allowDuplicate": entry.get("allowDuplicate", True),
        "emptyValue": entry.get("emptyValue", False),
        "defaultValue": entry.get("defaultValue"),
        "encodeEnabled": entry.get("encodeEnabled", False),
        "encodeMethod": entry.get("encodeMethod"),
        "encodePrefix": entry.get("encodePrefix"),
        "encodeMap": entry.get("encodeMap"),
        "encodeKey": entry.get("encodeKey"),
        "owner": entry.get("owner", ""),
        "ownerName": entry.get("owner", ""),
        "createdAt": entry.get("createdAt", 0),
    }
    if include_data:
        obj["data"] = entry.get("data", [])
    return obj


def paginate(items, page):
    page = max(1, int(page))
    total = len(items)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return items[start:end], page, pages


@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(PUBLIC_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(PUBLIC_DIR, "js"), filename)


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/auth")
def auth_page():
    return send_from_directory(PUBLIC_DIR, "auth.html")


@app.route("/admin")
def admin_page():
    return send_from_directory(PUBLIC_DIR, "admin.html")


@app.route("/manager")
def manager_page():
    return send_from_directory(PUBLIC_DIR, "manager.html")


@app.route("/manager-user")
def manager_user_page():
    return send_from_directory(PUBLIC_DIR, "manager-user.html")


@app.route("/view")
def view_page():
    return send_from_directory(PUBLIC_DIR, "view.html")


@app.route("/error")
def error_page():
    return send_from_directory(PUBLIC_DIR, "error.html")


@app.route("/api")
@app.route("/api/")
def api_index():
    return jsonify({"name": "Lonely Hub API", "status": "ok", "totalExecute": get_execute_count()})


@app.route("/api/healthz")
def healthz():
    return jsonify({"status": "ok"})


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
    if username.lower() == "longhip12" and user.get("role") != "admin":
        users = get_users()
        users[user["id"]]["role"] = "admin"
        save_users(users)
        user = users[user["id"]]
    session["user_id"] = user["id"]
    return jsonify({"success": True, "user": user_to_public(user)})


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
    return jsonify({"success": True, "user": user_to_public(users[uid])}), 201


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/me")
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"loggedIn": False}), 200
    return jsonify({"loggedIn": True, "user": user_to_public(user)})


@app.route("/api/manage/apis", methods=["GET"])
@login_required
def manage_list_apis():
    user = get_current_user()
    reg = get_registry()
    all_apis = list(reg.values())
    all_apis.sort(key=lambda a: a.get("createdAt", 0), reverse=True)
    if not is_admin(user):
        all_apis = [a for a in all_apis if a.get("owner", "").lower() == user["username"].lower()]
    page_param = request.args.get("page")
    if page_param is None:
        return jsonify({"apis": [api_to_public(a) for a in all_apis], "page": 1, "pages": 1})
    items, page, pages = paginate(all_apis, page_param)
    return jsonify({"apis": [api_to_public(a) for a in items], "page": page, "pages": pages})


@app.route("/api/manage/apis", methods=["POST"])
@login_required
def manage_create_api():
    user = get_current_user()
    body = request.get_json(silent=True) or {}
    api_id = str(body.get("apiId", "")).strip()
    api_name = str(body.get("apiName", "")).strip()
    if not api_id or not api_name:
        return jsonify({"error": "apiId and apiName are required"}), 400
    reg = get_registry()
    for entry in reg.values():
        if entry["apiId"] == api_id and entry["apiName"].lower() == api_name.lower():
            return jsonify({"error": "API with this ID and name already exists"}), 409
    internal_id = str(uuid.uuid4())
    whitelist_raw = body.get("whitelistIps", "")
    whitelist = [ip.strip() for ip in whitelist_raw.split(",") if ip.strip()] if isinstance(whitelist_raw, str) else (whitelist_raw or [])
    rate_limit = body.get("rateLimit")
    if rate_limit is not None:
        try:
            rate_limit = int(rate_limit)
        except Exception:
            rate_limit = None
    entry = {
        "id": internal_id,
        "apiId": api_id,
        "apiName": api_name,
        "displayName": str(body.get("displayName", api_name)).strip() or api_name,
        "webhookUrl": str(body.get("webhookUrl", "")).strip(),
        "visibility": body.get("visibility", "Public") if body.get("visibility") in ("Public", "Private") else "Public",
        "whitelistIps": whitelist,
        "rateLimit": rate_limit,
        "allowDuplicate": bool(body.get("allowDuplicate", True)),
        "emptyValue": bool(body.get("emptyValue", False)),
        "defaultValue": body.get("defaultValue") if not body.get("emptyValue") else None,
        "encodeEnabled": bool(body.get("encodeEnabled", False)),
        "encodeMethod": body.get("encodeMethod") if body.get("encodeEnabled") else None,
        "encodePrefix": body.get("encodePrefix") if body.get("encodeEnabled") else None,
        "encodeMap": body.get("encodeMap") if body.get("encodeEnabled") else None,
        "encodeKey": body.get("encodeKey") if body.get("encodeEnabled") else None,
        "owner": user["username"],
        "data": [],
        "createdAt": int(time.time()),
    }
    reg[internal_id] = entry
    save_registry(reg)
    return jsonify({"success": True, "api": api_to_public(entry)}), 201


@app.route("/api/manage/apis/<internal_id>", methods=["PUT"])
@login_required
def manage_edit_api(internal_id):
    user = get_current_user()
    reg = get_registry()
    entry = reg.get(internal_id)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    if not is_admin(user) and entry.get("owner", "").lower() != user["username"].lower():
        return jsonify({"error": "Forbidden"}), 403
    body = request.get_json(silent=True) or {}
    if "apiName" in body:
        entry["apiName"] = str(body["apiName"]).strip() or entry["apiName"]
    if "displayName" in body:
        entry["displayName"] = str(body["displayName"]).strip() or entry["apiName"]
    if "webhookUrl" in body:
        entry["webhookUrl"] = str(body["webhookUrl"]).strip()
    if "visibility" in body and body["visibility"] in ("Public", "Private"):
        entry["visibility"] = body["visibility"]
    if "whitelistIps" in body:
        raw = body["whitelistIps"]
        entry["whitelistIps"] = [ip.strip() for ip in raw.split(",") if ip.strip()] if isinstance(raw, str) else (raw or [])
    if "rateLimit" in body:
        try:
            entry["rateLimit"] = int(body["rateLimit"]) if body["rateLimit"] else None
        except Exception:
            entry["rateLimit"] = None
    if "allowDuplicate" in body:
        entry["allowDuplicate"] = bool(body["allowDuplicate"])
    if "emptyValue" in body:
        entry["emptyValue"] = bool(body["emptyValue"])
    if "defaultValue" in body:
        entry["defaultValue"] = body["defaultValue"] if not entry.get("emptyValue") else None
    if "encodeEnabled" in body:
        entry["encodeEnabled"] = bool(body["encodeEnabled"])
    if "encodeMethod" in body:
        entry["encodeMethod"] = body["encodeMethod"] if entry.get("encodeEnabled") else None
    if "encodePrefix" in body:
        entry["encodePrefix"] = body["encodePrefix"] if entry.get("encodeEnabled") else None
    if "encodeMap" in body:
        entry["encodeMap"] = body["encodeMap"] if entry.get("encodeEnabled") else None
    if "encodeKey" in body:
        entry["encodeKey"] = body["encodeKey"] if entry.get("encodeEnabled") else None
    reg[internal_id] = entry
    save_registry(reg)
    return jsonify({"success": True, "api": api_to_public(entry)})


@app.route("/api/manage/apis/<internal_id>", methods=["DELETE"])
@login_required
def manage_delete_api(internal_id):
    user = get_current_user()
    reg = get_registry()
    entry = reg.get(internal_id)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    if not is_admin(user) and entry.get("owner", "").lower() != user["username"].lower():
        return jsonify({"error": "Forbidden"}), 403
    del reg[internal_id]
    save_registry(reg)
    return jsonify({"success": True})


@app.route("/api/manage/apis/<internal_id>/reset", methods=["POST"])
@login_required
def manage_reset_api(internal_id):
    user = get_current_user()
    reg = get_registry()
    entry = reg.get(internal_id)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    if not is_admin(user) and entry.get("owner", "").lower() != user["username"].lower():
        return jsonify({"error": "Forbidden"}), 403
    entry["data"] = []
    reg[internal_id] = entry
    save_registry(reg)
    return jsonify({"success": True})


@app.route("/api/manage/users", methods=["GET"])
@admin_required
def manage_list_users():
    users = get_users()
    all_users = [user_to_public(u) for u in users.values()]
    all_users.sort(key=lambda u: u.get("createdAt", 0), reverse=True)
    page_param = request.args.get("page")
    if page_param is None:
        return jsonify({"users": all_users, "page": 1, "pages": 1})
    items, page, pages = paginate(all_users, page_param)
    return jsonify({"users": items, "page": page, "pages": pages})


@app.route("/api/manage/users/<uid>/permission", methods=["PUT"])
@admin_required
def manage_toggle_user_permission(uid):
    users = get_users()
    if uid not in users:
        return jsonify({"error": "User not found"}), 404
    current_role = users[uid].get("role", "member")
    users[uid]["role"] = "member" if current_role == "admin" else "admin"
    save_users(users)
    return jsonify({"success": True, "user": user_to_public(users[uid])})


@app.route("/api/manage/users/<uid>", methods=["DELETE"])
@admin_required
def manage_delete_user(uid):
    users = get_users()
    if uid not in users:
        return jsonify({"error": "User not found"}), 404
    del users[uid]
    save_users(users)
    return jsonify({"success": True})


def find_api_entry(api_id, api_name):
    reg = get_registry()
    for entry in reg.values():
        if entry["apiId"] == api_id and entry["apiName"].lower() == api_name.lower():
            return entry
    return None


def encode_value(value, method, encode_map=None, prefix=""):
    if method == "Base64":
        import base64
        encoded = base64.b64encode(str(value).encode()).decode()
        return (prefix or "") + encoded
    elif method == "Hex":
        encoded = str(value).encode().hex()
        return (prefix or "") + encoded
    elif method == "Binary":
        encoded = " ".join(format(b, "08b") for b in str(value).encode())
        return (prefix or "") + encoded
    elif method == "Unicode Escaped":
        encoded = str(value).encode("unicode_escape").decode()
        return (prefix or "") + encoded
    elif method == "Custom" and encode_map:
        result = ""
        for ch in str(value):
            result += encode_map.get(ch, ch)
        return (prefix or "") + result
    return value


@app.route("/api/v4/<api_id>/<api_name>", methods=["GET"])
def v4_get(api_id, api_name):
    entry = find_api_entry(api_id, api_name)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    ip = get_ip(request)
    if entry.get("visibility") == "Private":
        whitelist = entry.get("whitelistIps", [])
        if whitelist and ip not in whitelist:
            return jsonify({"error": "Access denied"}), 403
    rate = entry.get("rateLimit")
    if rate:
        if not check_rate_limit(f"v4:{api_id}:{api_name}:{ip}", rate):
            return jsonify({"error": f"Rate limit exceeded. Max {rate} req/min"}), 429
    data = entry.get("data", [])
    if not data and not entry.get("emptyValue") and entry.get("defaultValue") is not None:
        data = [entry["defaultValue"]]
    return jsonify({"success": True, "apiId": api_id, "apiName": api_name, "data": data})


@app.route("/api/v4/<api_id>/<api_name>", methods=["POST"])
def v4_send(api_id, api_name):
    entry = find_api_entry(api_id, api_name)
    if not entry:
        return jsonify({"error": "API not found"}), 404
    ip = get_ip(request)
    rate = entry.get("rateLimit")
    if rate:
        if not check_rate_limit(f"v4:send:{api_id}:{api_name}:{ip}", rate):
            return jsonify({"error": f"Rate limit exceeded. Max {rate} req/min"}), 429
    body = request.get_json(silent=True) or {}
    reg = get_registry()
    internal_id = entry["id"]
    current_entry = reg.get(internal_id, entry)
    data_list = current_entry.get("data", [])
    if not current_entry.get("allowDuplicate") and body in data_list:
        return jsonify({"error": "Duplicate data not allowed"}), 409
    encode_key = current_entry.get("encodeKey")
    if current_entry.get("encodeEnabled") and encode_key and encode_key in body:
        method = current_entry.get("encodeMethod", "Base64")
        body[encode_key] = encode_value(
            body[encode_key],
            method,
            encode_map=current_entry.get("encodeMap"),
            prefix=current_entry.get("encodePrefix", ""),
        )
    data_list.append(body)
    current_entry["data"] = data_list
    reg[internal_id] = current_entry
    save_registry(reg)
    webhook = current_entry.get("webhookUrl", "")
    if webhook:
        header_lines = "\n".join(f"    + {k}: {v}" for k, v in body.items())
        content = f"# API Post Detected!\n- **API Name**: {current_entry['apiName']}\n- **API ID**: {api_id}\n- **Headers**:\n{header_lines}"
        try:
            requests.post(webhook, json={"content": content}, timeout=10)
        except Exception:
            pass
    return jsonify({"success": True})


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


def _v1_lookup_and_return(name):
    ip = get_ip(request)
    reg = get_registry()
    matches = [e for e in reg.values() if e["apiName"].lower() == name.lower() or e["apiId"].lower() == name.lower()]
    if matches:
        entry = matches[0]
        if entry.get("visibility") == "Private":
            whitelist = entry.get("whitelistIps", [])
            if whitelist and ip not in whitelist:
                return jsonify({"error": "Access denied"}), 403
        rate = entry.get("rateLimit")
        if rate and not check_rate_limit(f"v1:get:{name}:{ip}", rate):
            return jsonify({"error": f"Rate limit exceeded. Max {rate} req/min"}), 429
        data = entry.get("data", [])
        if not data and not entry.get("emptyValue") and entry.get("defaultValue") is not None:
            data = [entry["defaultValue"]]
        return jsonify({"success": True, "apiId": entry["apiId"], "apiName": entry["apiName"], "data": data})
    old_reg = read_json("apiRegistry", {})
    for api_id, entry in old_reg.items():
        if entry.get("apiName", "").lower() == name.lower() or api_id.lower() == name.lower():
            default_value = entry.get("defaultValue")
            data = [default_value] if default_value is not None else []
            return jsonify({"success": True, "apiId": api_id, "apiName": entry["apiName"], "data": data})
    return jsonify({"error": "API not found"}), 404


@app.route("/api/v1/<name>", methods=["GET"])
def v1_get(name):
    return _v1_lookup_and_return(name)


@app.route("/api/v1/bloxfruit/<name>", methods=["GET", "POST"])
def v1_bloxfruit(name):
    if request.method == "GET":
        return _v1_lookup_and_return(name)
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
