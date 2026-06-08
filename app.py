import os
import json
import secrets
import hashlib
import base64
import time
from datetime import datetime
from functools import wraps
from threading import Lock

from flask import Flask, request, session, jsonify, send_from_directory

try:
    import bcrypt
    _USE_BCRYPT = True
except ImportError:
    _USE_BCRYPT = False

import requests

app = Flask(__name__, static_folder="public", static_url_path="")
app.secret_key = os.environ.get("SESSION_SECRET", "lonely-hub-secret-key")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 7 * 24 * 3600

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

_locks: dict[str, Lock] = {}

def _lock(name):
    if name not in _locks:
        _locks[name] = Lock()
    return _locks[name]

def read_json(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        if filename == "bloxfruit.json":
            return {"servers": {}}
        return []

def write_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with _lock(filename):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

_rate: dict[str, dict] = {}

def check_rate_limit(key, limit_per_min):
    now = time.time()
    entry = _rate.get(key)
    if not entry or now > entry["reset_at"]:
        _rate[key] = {"count": 1, "reset_at": now + 60}
        return True
    if entry["count"] >= limit_per_min:
        return False
    entry["count"] += 1
    return True

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

def _encode_base62(s):
    num = int(s.encode().hex(), 16)
    if num == 0:
        return "0"
    result = ""
    while num:
        result = BASE62[num % 62] + result
        num //= 62
    return result

def _encode_base32(s):
    data = s.encode()
    result = ""
    bits = current = 0
    for byte in data:
        current = (current << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            result += BASE32[(current >> bits) & 0x1f]
    if bits:
        result += BASE32[(current << (5 - bits)) & 0x1f]
    return result

def encode_value(value, method, encode_map=None, prefix=None):
    if method == "Base64":
        return base64.b64encode(value.encode()).decode()
    if method == "Base62":
        return _encode_base62(value)
    if method == "Base32":
        return _encode_base32(value)
    if method == "Hex":
        return value.encode().hex()
    if method == "Binary":
        return " ".join(format(ord(c), "08b") for c in value)
    if method == "Unicode Escaped":
        return "".join(f"\\u{ord(c):04x}" for c in value)
    if method == "Custom" and encode_map:
        encoded = "".join(encode_map.get(c, c) for c in value)
        return (prefix or "") + encoded
    return value

def apply_encode(data, key, method, encode_map=None, prefix=None):
    result = dict(data)
    if key in result:
        result[key] = encode_value(str(result[key]), method, encode_map, prefix)
    return result

def apply_random_encode(data, key, encode_data):
    keys = list(encode_data.keys())
    if not keys:
        return data
    chosen = keys[secrets.randbelow(len(keys))]
    encode_set = encode_data[chosen]
    prefix = encode_set.get("Prefix", "")
    encode_map = {k: v for k, v in encode_set.items() if k != "Prefix" and v}
    return apply_encode(data, key, "Custom", encode_map, prefix)

def _hash_password(password):
    if _USE_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha256:{salt}:{h}"

def _check_password(password, hashed):
    if _USE_BCRYPT and not hashed.startswith("sha256:"):
        return bcrypt.checkpw(password.encode(), hashed.encode())
    try:
        _, salt, h = hashed.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False

def send_discord_webhook(webhook_url, display_name, ip, headers):
    skip = {"host", "connection", "content-length", "transfer-encoding"}
    lines = [f"- **{k}**: {v}" for k, v in headers.items() if k.lower() not in skip]
    content = f"**{display_name} API Webhook**\nPost By: {ip or 'N/A'}\n" + "\n".join(lines)
    try:
        requests.post(webhook_url, json={"content": content}, timeout=5)
    except Exception:
        pass

def get_ip():
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "N/A"

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return wrapper

def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Not logged in"}), 401
        if not session.get("is_admin"):
            return jsonify({"error": "Admin required"}), 403
        return f(*args, **kwargs)
    return wrapper

PUBLIC = os.path.join(BASE_DIR, "public")

def serve_page(page):
    path = os.path.join(PUBLIC, f"{page}.html")
    if os.path.exists(path):
        return send_from_directory(PUBLIC, f"{page}.html")
    return jsonify({"error": "Page not found"}), 404

@app.route("/")
def index():
    return serve_page("index")

@app.route("/auth")
def auth():
    return serve_page("auth")

@app.route("/manager")
def manager():
    return serve_page("manager")

@app.route("/view")
def view():
    return serve_page("view")

@app.route("/admin")
def admin():
    return serve_page("admin")

@app.route("/manager-user")
def manager_user():
    return serve_page("manager-user")

@app.route("/error")
def error_page():
    return serve_page("error")

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    users = read_json("users.json")
    user = next((u for u in users if u["username"] == username), None)
    if not user or not _check_password(password, user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401
    session.permanent = True
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["is_admin"] = user["isAdmin"]
    return jsonify({"success": True, "user": {"id": user["id"], "username": user["username"], "isAdmin": user["isAdmin"]}})

@app.route("/api/auth/register", methods=["POST"])
def register():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    users = read_json("users.json")
    if any(u["username"] == username for u in users):
        return jsonify({"error": "Username already taken"}), 409
    is_admin = len(users) == 0
    new_user = {
        "id": secrets.token_hex(8),
        "username": username,
        "password": _hash_password(password),
        "isAdmin": is_admin,
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    users.append(new_user)
    write_json("users.json", users)
    session.permanent = True
    session["user_id"] = new_user["id"]
    session["username"] = new_user["username"]
    session["is_admin"] = new_user["isAdmin"]
    return jsonify({"success": True, "user": {"id": new_user["id"], "username": new_user["username"], "isAdmin": new_user["isAdmin"]}})

@app.route("/api/auth/me")
def me():
    if not session.get("user_id"):
        return jsonify({"loggedIn": False})
    return jsonify({"loggedIn": True, "user": {"id": session["user_id"], "username": session["username"], "isAdmin": session["is_admin"]}})

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/healthz")
def healthz():
    return jsonify({"status": "ok"})

@app.route("/api/manage/apis")
@require_auth
def list_apis():
    apis = read_json("apis.json")
    page = max(1, int(request.args.get("page", 1)))
    page_size = 15
    all_apis = apis if session.get("is_admin") else [a for a in apis if a["ownerId"] == session["user_id"]]
    total = len(all_apis)
    paged = all_apis[(page - 1) * page_size: page * page_size]
    return jsonify({"apis": paged, "total": total, "page": page, "pages": max(1, -(-total // page_size))})

def _parse_api_body(body, existing=None):
    def g(k, default=None):
        return body.get(k, existing.get(k, default) if existing else default)
    encode_enabled = bool(g("encodeEnabled", False))
    encode_method = g("encodeMethod") if encode_enabled else None
    visibility = g("visibility", "Public")
    whitelist_raw = g("whitelistIps", "")
    if visibility == "Private" and whitelist_raw:
        whitelist = [ip.strip() for ip in str(whitelist_raw).split(",") if ip.strip()]
    elif visibility == "Public":
        whitelist = []
    else:
        whitelist = existing.get("whitelistIps", []) if existing else []
    empty_value = bool(g("emptyValue", False))
    return {
        "apiId": g("apiId") or secrets.token_hex(5),
        "apiName": g("apiName") or secrets.token_hex(5),
        "displayName": g("displayName") or g("apiName") or "",
        "emptyValue": empty_value,
        "defaultValue": None if empty_value else g("defaultValue"),
        "webhookUrl": g("webhookUrl") or None,
        "visibility": visibility if visibility in ("Public", "Private") else "Public",
        "whitelistIps": whitelist,
        "rateLimit": int(g("rateLimit")) if g("rateLimit") else None,
        "allowDuplicate": bool(g("allowDuplicate", False)),
        "encodeEnabled": encode_enabled,
        "encodeMethod": encode_method,
        "encodePrefix": g("encodePrefix") if encode_enabled and encode_method == "Custom" else None,
        "encodeMap": g("encodeMap") if encode_enabled and encode_method == "Custom" else None,
        "encodeKey": g("encodeKey") if encode_enabled else None,
    }

@app.route("/api/manage/apis", methods=["POST"])
@require_auth
def create_api():
    body = request.get_json() or {}
    apis = read_json("apis.json")
    fields = _parse_api_body(body)
    new_api = {
        "id": secrets.token_hex(8),
        **fields,
        "displayName": fields["displayName"] or fields["apiName"],
        "ownerId": session["user_id"],
        "ownerName": session["username"],
        "data": [],
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    apis.append(new_api)
    write_json("apis.json", apis)
    return jsonify({"success": True, "api": {"id": new_api["id"], "apiId": new_api["apiId"], "apiName": new_api["apiName"]}})

@app.route("/api/manage/apis/<api_id>", methods=["PUT"])
@require_auth
def update_api(api_id):
    apis = read_json("apis.json")
    idx = next((i for i, a in enumerate(apis) if a["id"] == api_id), -1)
    if idx == -1:
        return jsonify({"error": "API not found"}), 404
    if apis[idx]["ownerId"] != session["user_id"] and not session.get("is_admin"):
        return jsonify({"error": "Forbidden"}), 403
    fields = _parse_api_body(request.get_json() or {}, apis[idx])
    apis[idx] = {**apis[idx], **fields}
    write_json("apis.json", apis)
    return jsonify({"success": True})

@app.route("/api/manage/apis/<api_id>", methods=["DELETE"])
@require_auth
def delete_api(api_id):
    apis = read_json("apis.json")
    idx = next((i for i, a in enumerate(apis) if a["id"] == api_id), -1)
    if idx == -1:
        return jsonify({"error": "API not found"}), 404
    if apis[idx]["ownerId"] != session["user_id"] and not session.get("is_admin"):
        return jsonify({"error": "Forbidden"}), 403
    apis.pop(idx)
    write_json("apis.json", apis)
    return jsonify({"success": True})

@app.route("/api/manage/apis/<api_id>/reset", methods=["POST"])
@require_auth
def reset_api(api_id):
    apis = read_json("apis.json")
    idx = next((i for i, a in enumerate(apis) if a["id"] == api_id), -1)
    if idx == -1:
        return jsonify({"error": "API not found"}), 404
    if apis[idx]["ownerId"] != session["user_id"] and not session.get("is_admin"):
        return jsonify({"error": "Forbidden"}), 403
    apis[idx]["data"] = []
    write_json("apis.json", apis)
    return jsonify({"success": True})

@app.route("/api/manage/users")
@require_admin
def list_users():
    page = max(1, int(request.args.get("page", 1)))
    page_size = 15
    users = read_json("users.json")
    total = len(users)
    paged = [{"id": u["id"], "username": u["username"], "isAdmin": u["isAdmin"], "createdAt": u["createdAt"]} for u in users[(page - 1) * page_size: page * page_size]]
    return jsonify({"users": paged, "total": total, "page": page, "pages": max(1, -(-total // page_size))})

@app.route("/api/manage/users/<user_id>/permission", methods=["PUT"])
@require_admin
def toggle_permission(user_id):
    users = read_json("users.json")
    idx = next((i for i, u in enumerate(users) if u["id"] == user_id), -1)
    if idx == -1:
        return jsonify({"error": "User not found"}), 404
    users[idx]["isAdmin"] = not users[idx]["isAdmin"]
    write_json("users.json", users)
    return jsonify({"success": True, "isAdmin": users[idx]["isAdmin"]})

@app.route("/api/manage/users/<user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    if user_id == session.get("user_id"):
        return jsonify({"error": "Cannot delete yourself"}), 400
    users = read_json("users.json")
    idx = next((i for i, u in enumerate(users) if u["id"] == user_id), -1)
    if idx == -1:
        return jsonify({"error": "User not found"}), 404
    users.pop(idx)
    write_json("users.json", users)
    return jsonify({"success": True})

def _build_response(api):
    if api.get("emptyValue"):
        return {}
    return {
        "source": "python 3.15",
        "success": True,
        "owner": api["ownerName"],
        "id": api["apiId"],
        "name": api["displayName"],
        "total": str(len(api.get("data", []))),
        "data": api.get("data", []),
    }

@app.route("/v4/<api_id>/all")
def dynamic_all(api_id):
    apis = read_json("apis.json")
    matching = [a for a in apis if a["apiId"] == api_id]
    if not matching:
        return jsonify({"error": "API not found"}), 404
    return jsonify({a["apiName"]: _build_response(a) for a in matching})

@app.route("/v4/<api_id>/<api_name>", methods=["GET"])
def dynamic_get(api_id, api_name):
    apis = read_json("apis.json")
    api = next((a for a in apis if a["apiId"] == api_id and a["apiName"] == api_name), None)
    if not api:
        return jsonify({"error": "API not found"}), 404
    ip = get_ip()
    if api["visibility"] == "Private" and api.get("whitelistIps") and ip not in api["whitelistIps"]:
        return jsonify({"err": "You do not have permission to access this API"}), 403
    return jsonify(_build_response(api))

@app.route("/v4/<api_id>/<api_name>", methods=["POST"])
def dynamic_post(api_id, api_name):
    apis = read_json("apis.json")
    idx = next((i for i, a in enumerate(apis) if a["apiId"] == api_id and a["apiName"] == api_name), -1)
    if idx == -1:
        return jsonify({"error": "API not found"}), 404
    api = apis[idx]
    ip = get_ip()
    if api["visibility"] == "Private" and api.get("whitelistIps") and ip not in api["whitelistIps"]:
        return jsonify({"err": "You do not have permission to access this API"}), 403
    if api.get("rateLimit"):
        if not check_rate_limit(f"v4:{api_id}:{api_name}:{ip}", api["rateLimit"]):
            return jsonify({"error": "Rate limit exceeded"}), 429
    body = request.get_json() or {}
    if api.get("encodeEnabled") and api.get("encodeMethod") and api.get("encodeKey"):
        body = apply_encode(body, api["encodeKey"], api["encodeMethod"], api.get("encodeMap"), api.get("encodePrefix"))
    if not api.get("allowDuplicate"):
        if any(json.dumps(d, sort_keys=True) == json.dumps(body, sort_keys=True) for d in api.get("data", [])):
            return jsonify({"error": "Duplicate data"}), 409
    apis[idx].setdefault("data", []).append(body)
    write_json("apis.json", apis)
    if api.get("webhookUrl"):
        send_discord_webhook(api["webhookUrl"], api["displayName"], ip, dict(request.headers))
    return jsonify(_build_response(apis[idx]))

@app.route("/v3/<api_id>/send/<api_name>", methods=["POST"])
def v3_send(api_id, api_name):
    apis = read_json("apis.json")
    api = next((a for a in apis if a["apiId"] == api_id and a["apiName"] == api_name), None)
    if not api or not api.get("webhookUrl"):
        return jsonify({"error": "API or webhook not found"}), 404
    ip = get_ip()
    if api.get("rateLimit"):
        if not check_rate_limit(f"v3:{api_id}:{api_name}:{ip}", api["rateLimit"]):
            return jsonify({"error": "Rate limit exceeded"}), 429
    body = request.get_json() or {}
    content = body.get("content", json.dumps(body))
    content = content.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    try:
        requests.post(api["webhookUrl"], json={"content": content}, timeout=5)
        return jsonify({"success": True})
    except Exception:
        return jsonify({"error": "Failed to send webhook"}), 500

def _get_encode_data():
    try:
        return json.loads(os.environ.get("ENCODE_DATA", "{}"))
    except Exception:
        return {}

@app.route("/v1/bloxfruit/all")
def bloxfruit_all():
    bf = read_json("bloxfruit.json")
    all_data = [item for arr in bf.get("servers", {}).values() for item in arr]
    return jsonify({"source": "python 3.15", "success": True, "total": str(len(all_data)), "data": all_data})

@app.route("/v1/bloxfruit/<server>", methods=["GET"])
def bloxfruit_get(server):
    bf = read_json("bloxfruit.json")
    data = bf.get("servers", {}).get(server, [])
    return jsonify({"source": "python 3.15", "success": True, "total": str(len(data)), "data": data})

@app.route("/v1/bloxfruit/<server>", methods=["POST"])
def bloxfruit_post(server):
    bf = read_json("bloxfruit.json")
    bf.setdefault("servers", {}).setdefault(server, [])
    body = request.get_json() or {}
    encode_data = _get_encode_data()
    if encode_data:
        body = apply_random_encode(body, "JobId", encode_data)
    bf["servers"][server].append(body)
    write_json("bloxfruit.json", bf)
    all_data = [item for arr in bf["servers"].values() for item in arr]
    return jsonify({"source": "python 3.15", "success": True, "total": str(len(all_data)), "data": bf["servers"][server]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Server running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
