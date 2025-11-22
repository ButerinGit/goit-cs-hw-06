import os
import json
import socket
import multiprocessing
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from pathlib import Path

from pymongo import MongoClient

# Налаштування портів
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 3000

SOCKET_HOST = "0.0.0.0"   # слухаємо на всіх інтерфейсах
SOCKET_PORT = 5000

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


# ---------- MongoDB ----------

def get_mongo_collection():
    """
    Повертає колекцію MongoDB для збереження повідомлень.
    URI беремо з змінної оточення MONGO_URI або використовуємо localhost.
    """
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri)
    db = client["messages_db"]
    collection = db["messages"]
    return collection


# ---------- Socket-сервер (порт 5000) ----------

def run_socket_server():
    """
    Socket-сервер (TCP) слухає порт 5000, отримує JSON від вебдодатку,
    додає поле date і записує документ у MongoDB.
    """
    collection = get_mongo_collection()
    print(f"[Socket] Starting socket server on {SOCKET_HOST}:{SOCKET_PORT}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((SOCKET_HOST, SOCKET_PORT))
        server_sock.listen(5)

        while True:
            conn, addr = server_sock.accept()
            with conn:
                try:
                    data = conn.recv(4096)
                    if not data:
                        continue

                    # bytes -> str -> dict
                    payload = json.loads(data.decode("utf-8"))

                    # додати час отримання
                    payload["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

                    # зберегти в MongoDB
                    collection.insert_one(payload)
                    print(f"[Socket] Saved message from {payload.get('username')}")
                except Exception as e:
                    print("[Socket] Error:", e)


def send_to_socket_server(payload: dict):
    """
    Клієнтська функція: відправляє dict (username, message) на socket-сервер.
    """
    data = json.dumps(payload).encode("utf-8")

    # У цьому ж контейнері socket-сервер слухає на localhost:5000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(("127.0.0.1", SOCKET_PORT))
        sock.sendall(data)


# ---------- HTTP-сервер (порт 3000) ----------

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.serve_html("index.html")
        elif self.path in ("/message", "/message.html"):
            self.serve_html("message.html")
        elif self.path == "/style.css":
            self.serve_static("static/style.css", "text/css")
        elif self.path == "/logo.png":
            self.serve_static("static/logo.png", "image/png")
        else:
            self.serve_error(404)

    def do_POST(self):
        if self.path in ("/message", "/message.html"):
            self.handle_message_form()
        else:
            self.serve_error(404)

    # ---- допоміжні методи ----

    def handle_message_form(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            data = parse_qs(body)
            username = data.get("username", [""])[0]
            message = data.get("message", [""])[0]

            if username and message:
                payload = {
                    "username": username,
                    "message": message
                }
                # Надіслати дані Socket-серверу
                send_to_socket_server(payload)

            # Після відправки можемо зробити редірект, наприклад, на index.html
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()

        except Exception as e:
            print("[HTTP] Error handling POST:", e)
            self.serve_error(500)

    def serve_html(self, filename: str, status_code: int = 200):
        path = TEMPLATES_DIR / filename
        if not path.exists():
            self.serve_error(404)
            return

        try:
            with open(path, "rb") as f:
                content = f.read()

            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            print("[HTTP] Error serving HTML:", e)
            self.serve_error(500)

    def serve_static(self, filename: str, content_type: str):
        path = STATIC_DIR / filename
        if not path.exists():
            self.serve_error(404)
            return

        try:
            with open(path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            print("[HTTP] Error serving static:", e)
            self.serve_error(500)

    def serve_error(self, code: int):
        """
        404 -> error.html
        500 -> простий текст + по можливості теж error.html
        """
        if code == 404:
            path = TEMPLATES_DIR / "error.html"
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if path.exists():
                with open(path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"<h1>404 Not Found</h1>")
        else:
            self.send_response(500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>500 Internal Server Error</h1>")

    def log_message(self, format, *args):
        # Щоб не засмічувати консоль стандартним логом http.server
        return


def run_http_server():
    httpd = HTTPServer((HTTP_HOST, HTTP_PORT), SimpleHTTPRequestHandler)
    print(f"[HTTP] Starting HTTP server on {HTTP_HOST}:{HTTP_PORT}")
    httpd.serve_forever()


# ---------- Точка входу: два процеси ----------

if __name__ == "__main__":
    socket_proc = multiprocessing.Process(target=run_socket_server, daemon=True)
    http_proc = multiprocessing.Process(target=run_http_server)

    socket_proc.start()
    http_proc.start()

    socket_proc.join()
    http_proc.join()