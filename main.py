import datetime
import json
import logging
import mimetypes
import pathlib
import socket
import urllib.parse

from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


"""
Простий веб додаток на 2 сторінки.
index.html та message.html
На сторінці message.html реалізовано отримання даних з форми,
данні зберігаються в storage/data.json
"""


BASE_DIR = pathlib.Path()
SERVER_IP = "127.0.0.1"  # ip socket server
SERVER_PORT = 5000  # port socket server
BUFFER = 1024  #


def send_data_to_socket(body):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP, SERVER_PORT))
    client_socket.close()


class HTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header("Location", "/index")
        self.end_headers()

    def do_GET(self):
        """
        Маршрутизація сторінок.
        :return:
        """
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html("index.html")
            case "/index":
                self.send_html("index.html")
            case "/message":
                self.send_html("message.html")
            case _:
                file = BASE_DIR / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)

    def send_html(self, filename, status_code=200):
        """
        Відправлення html сторінки.
        :param filename:
        :param status_code:
        :return:
        """
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_static(self, filename):
        """
        Відправлення статичних ресурсів за допомогою mimetypes.
        :param filename:
        :return:
        """
        self.send_response(200)
        mime_type, *rest = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header("Content-Type", mime_type)
        else:
            self.send_header("Content-Type", "text/plain")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())


def run(server=HTTPServer, handler=HTTPHandler):
    """
    Запсук сервера localhost.
    Порт 3000
    :param server:
    :param handler:
    :return:
    """
    address = ("0.0.0.0", 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def save_data(data):
    """
    Збереження данних з форми message.html у файл storage/data.json
    :param data:
    :return:
    """
    body = urllib.parse.unquote_plus(data.decode())
    try:
        with open(BASE_DIR.joinpath("storage/data.json")) as fd_r:
            data = json.load(fd_r)

        payload = {
            key: value for key, value in [el.split("=") for el in body.split("&")]
        }
        data[datetime.datetime.now().__str__()] = payload

        with open(BASE_DIR.joinpath("storage/data.json"), "w", encoding="utf-8") as fd_w:
            json.dump(data, fd_w, ensure_ascii=False, indent=4)

    except ValueError as err:
        logging.error(f"Field parse data {body} with error {err}")
    except OSError as err:
        logging.error(f"Field write or read data {body} with error {err}")


def run_socket_server(ip, port):
    """
    Запуск сокет сервера.
    :param ip:
    :param port:
    :return:
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)
    try:
        while True:
            data, address = server_socket.recvfrom(BUFFER)
            save_data(data)
    except KeyboardInterrupt:
        logging.info("Socket server stopped")
    finally:
        server_socket.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    STORAGE_DIR = pathlib.Path().joinpath("storage")
    FILE_STORAGE = STORAGE_DIR / "data.json"
    if not FILE_STORAGE.exists():
        with open(FILE_STORAGE, "w", encoding="utf-8") as fd:
            json.dump({}, fd, ensure_ascii=False)

    thread_server = Thread(target=run)
    thread_server.start()
    thread_socket = Thread(target=run_socket_server(SERVER_IP, SERVER_PORT))
    thread_socket.start()
