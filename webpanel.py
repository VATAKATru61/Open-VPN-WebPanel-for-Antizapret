from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import subprocess
import sqlite3
import os
import urllib.parse
import platform
import psutil
import socket
from datetime import datetime, timezone, timedelta

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="qqwweerrttyyuuiioopp")
templates = Jinja2Templates(directory="templates")

DB_PATH = "/root/vpn.db"
SCRIPT_PATH = "/root/antizapret/client.sh"


def get_clients():
    cmd = f"{SCRIPT_PATH} 3"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return []
    lines = result.stdout.split("\n")
    clients = [
        c.strip() for c in lines
        if c.strip() and not c.startswith("OpenVPN client names:")
        and c.strip() not in ["OpenVPN - List clients", "antizapret-client"]
    ]
    return clients


def get_user_id_by_profile(profile_name):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE profile_name=?", (profile_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_cert_expiry_info(client_name):
    cert_path = f"/etc/openvpn/easyrsa3/pki/issued/{client_name}.crt"
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", cert_path, "-noout", "-enddate"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0:
            return None
        not_after = result.stdout.strip().replace("notAfter=", "")
        date_to = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_left = (date_to - now).days
        return days_left
    except Exception:
        return None


def execute_script(option, client_name=None, days=None):
    command = f"{SCRIPT_PATH} {option}"
    if option in ["1", "9"] and client_name and days:
        command += f" {client_name} {days}"
    elif option == "2" and client_name:
        command += f" {client_name}"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode, result.stdout, result.stderr


def get_online_users_from_log():
    log_files = [
        "/etc/openvpn/server/logs/antizapret-tcp-status.log",
        "/etc/openvpn/server/logs/antizapret-udp-status.log",
        "/etc/openvpn/server/logs/vpn-tcp-status.log",
        "/etc/openvpn/server/logs/vpn-udp-status.log",
    ]
    online = set()
    for log_file in log_files:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("CLIENT_LIST,"):
                        fields = line.strip().split(",")
                        if len(fields) > 1:
                            online.add(fields[1])
        except Exception:
            continue
    return sorted(online)


def build_users():
    clients = get_clients()
    users = []
    for c in clients:
        user_id = get_user_id_by_profile(c)
        days_left = get_cert_expiry_info(c)
        users.append({
            "profile_name": c,
            "user_id": user_id,
            "days_left": days_left
        })
    return users


def get_server_stats():
    stats = {}
    # Аптайм
    uptime_seconds = float(os.popen('cat /proc/uptime').read().split()[0])
    stats['uptime'] = str(timedelta(seconds=int(uptime_seconds)))
    # CPU
    stats['cpu_percent'] = psutil.cpu_percent(interval=0.7)
    # RAM
    mem = psutil.virtual_memory()
    stats['ram_used'] = int(mem.used // 1024 // 1024)
    stats['ram_total'] = int(mem.total // 1024 // 1024)
    stats['ram_percent'] = mem.percent
    # Disk
    disk = psutil.disk_usage('/')
    stats['disk_free'] = int(disk.free // 1024 // 1024)
    stats['disk_total'] = int(disk.total // 1024 // 1024)
    stats['disk_percent'] = disk.percent
    # Hostname & IP
    stats['hostname'] = platform.node()
    try:
        stats['ip'] = socket.gethostbyname(socket.gethostname())
    except Exception:
        stats['ip'] = "Неизвестно"
    return stats


@app.get("/stats")
def get_stats():
    stats = get_server_stats()
    users = build_users()
    online_users = get_online_users_from_log()
    stats["users_count"] = len(users)
    stats["online_count"] = len(online_users)
    return JSONResponse(stats)


@app.get("/login")
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    password = form.get("password")
    if password == "Wtpmjgda1!":
        request.session["user"] = True
        return RedirectResponse("/", status_code=302)
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный пароль!"}
        )


def check_auth(request: Request):
    return bool(request.session.get("user"))


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    users = build_users()
    online_users = get_online_users_from_log()
    stats = get_server_stats()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "users": users,
        "online_users": online_users,
        "stats": stats,
        "message": "",
    })


@app.post("/", response_class=HTMLResponse)
async def users_actions(
    request: Request,
    action: str = Form(...),
    profile_name: str = Form(None),
    days: str = Form(None),
    new_user: str = Form(None)
):
    message = ""
    if action == "delete" and profile_name:
        code, out, err = execute_script("2", profile_name)
        if code == 0:
            message = f"Пользователь {profile_name} удалён."
        else:
            message = f"Ошибка удаления: {err or out}"
    elif action == "renew" and profile_name and days and days.isdigit():
        code, out, err = execute_script("9", profile_name, days)
        if code == 0:
            message = f"Срок действия {profile_name} обновлён на {days} дней."
        else:
            message = f"Ошибка продления: {err or out}"
    elif action == "add" and new_user:
        if not new_user or not new_user.replace("_", "").replace("-", "").isalnum():
            message = "Некорректное имя!"
        else:
            code, out, err = execute_script("1", new_user, "30")
            if code == 0:
                message = f"Пользователь {new_user} добавлен."
            else:
                message = f"Ошибка добавления: {err or out}"

    users = build_users()
    online_users = get_online_users_from_log()
    stats = get_server_stats()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "users": users,
        "online_users": online_users,
        "stats": stats,
        "message": message
    })


@app.get("/download/{kind}/{name}")
def download_config(kind: str, name: str, request: Request):
    if not check_auth(request):
        return RedirectResponse("/login")
    name = name.strip()
    if kind == "vpn":
        path = f"/root/antizapret/client/openvpn/vpn/ВСТАВЬ СВОЕ - Обычный VPN - {name}.ovpn"
    elif kind == "antizapret":
        path = f"/root/antizapret/client/openvpn/antizapret/ВСТАВЬ СВОЕ - {name}.ovpn"
    else:
        return RedirectResponse("/")
    if not os.path.exists(path):
        return RedirectResponse("/?error=not_found")
    filename = os.path.basename(path)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(filename)}"}
    return FileResponse(path, headers=headers, media_type="application/x-openvpn-profile")
