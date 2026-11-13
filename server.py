"""Local launcher and WSGI application for UNO Championship."""

import argparse
import json
import os
import secrets
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Lock
from time import monotonic
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from game import GameError, Player, Room


ROOT = Path(__file__).resolve().parent
ROOMS = {}
LOCK = Lock()
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
ASSETS = {
    "/": ("index.html", "text/html"),
    "/style.css": ("style.css", "text/css"),
    "/app.js": ("app.js", "text/javascript"),
}


class RequestError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def read_body(environ):
    if environ.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
        raise RequestError("415 Unsupported Media Type", "JSON 요청이 필요합니다.")
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        if not 1 <= length <= 4096:
            raise ValueError()
        data = json.loads(environ["wsgi.input"].read(length))
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, RecursionError) as error:
        raise RequestError("400 Bad Request", "요청 형식이 올바르지 않습니다.") from error


def new_player(data):
    name = data.get("name")
    name = " ".join(name.split()) if isinstance(name, str) else ""
    if not 1 <= len(name) <= 16 or not name.isprintable():
        raise GameError("닉네임은 1~16자로 입력해 주세요.")
    return Player(secrets.token_hex(6), secrets.token_urlsafe(24), name)


def authenticated(environ, code):
    room = ROOMS.get(code)
    if room is None:
        raise RequestError("404 Not Found", "방이 만료됐거나 서버가 다시 시작됐습니다.")
    token = environ.get("HTTP_AUTHORIZATION", "").removeprefix("Bearer ")
    if token.isascii():
        for member in room.players:
            if secrets.compare_digest(member.token, token):
                return room, member
    raise RequestError("401 Unauthorized", "입장 정보가 만료됐습니다.")


def api(environ, method, path, data):
    now = monotonic()
    for code in [code for code, room in ROOMS.items() if now - room.touched > 3600]:
        del ROOMS[code]

    if method == "POST" and path in {"/api/create", "/api/join"}:
        player = new_player(data)
        if path == "/api/create":
            if len(ROOMS) >= 150:
                raise GameError("서버의 방이 가득 찼습니다. 잠시 뒤 다시 시도해 주세요.")
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            while code in ROOMS:
                code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            room = ROOMS[code] = Room(code, [player])
            room.record(f"{player.name} 님이 방을 만들었습니다.")
        else:
            code = data.get("code")
            code = code.strip().upper() if isinstance(code, str) else ""
            room = ROOMS.get(code)
            if room is None:
                raise GameError("방을 찾을 수 없습니다. 방 코드를 확인해 주세요.")
            room.add(player)
        room.touched = now
        room.revision += 1
        return {"token": player.token, "state": room.view(player)}

    parts = path.split("/")
    if len(parts) != 5 or parts[1:3] != ["api", "room"]:
        raise RequestError("404 Not Found", "주소를 찾을 수 없습니다.")
    operation = parts[4]
    if (method, operation) not in {("GET", "state"), ("POST", "move"), ("POST", "leave")}:
        raise RequestError("404 Not Found", "주소를 찾을 수 없습니다.")
    room, player = authenticated(environ, parts[3])
    room.touched = now
    if operation == "leave":
        room.leave(player)
        room.revision += 1
        if not room.players:
            del ROOMS[room.code]
        return {}
    if operation == "move":
        if type(data.get("revision")) is not int or data["revision"] != room.revision:
            raise RequestError("409 Conflict", "게임 상태가 바뀌었습니다. 새 상태에서 다시 시도해 주세요.")
        if data.get("action") == "start":
            room.start(player)
        else:
            room.action(player, data)
        room.revision += 1
    return room.view(player)


def application(environ, start_response):
    method = environ["REQUEST_METHOD"]
    path = environ["PATH_INFO"]
    status = "200 OK"
    mime = "application/json"
    try:
        if method == "GET" and path in ASSETS:
            filename, mime = ASSETS[path]
            body = (ROOT / filename).read_bytes()
        elif method == "GET" and path == "/health":
            body = b'{"ok":true}'
        else:
            if not path.startswith("/api/") or method not in {"GET", "POST"}:
                raise RequestError("404 Not Found", "주소를 찾을 수 없습니다.")
            data = read_body(environ) if method == "POST" else {}
            with LOCK:
                result = api(environ, method, path, data)
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
    except (RequestError, GameError) as error:
        status = error.status if isinstance(error, RequestError) else "400 Bad Request"
        body = json.dumps({"error": str(error)}, ensure_ascii=False).encode("utf-8")
    start_response(status, [
        ("Content-Type", f"{mime}; charset=utf-8"), ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"),
    ])
    return [body]


class LocalServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, message, *args):
        if not self.path.endswith("/state"):
            super().log_message(message, *args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the UNO Championship server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    args = parser.parse_args()
    with make_server(args.host, args.port, application, LocalServer, QuietHandler) as server:
        print(f"UNO Championship: http://{args.host}:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
