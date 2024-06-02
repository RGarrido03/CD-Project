import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from typing import Generator, Any

from custom_types import Address
from p2p import P2PServer


class SudokuHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, p2p_server: P2PServer, **kwargs):
        super().__init__(*args, **kwargs)
        self.p2p_server = p2p_server

    def set_json_header(self):
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def send_success(self, body: dict = None):
        self.send_response(200)
        self.set_json_header()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def set_error(self, message: str):
        self.send_response(404)
        self.set_json_header()
        self.wfile.write(json.dumps({"message": message}).encode("utf-8"))

    def do_GET(self):
        logging.info(
            "GET request,\nsolve: %s\nstats:\n%network\n",
            str(self.path),
            str(self.headers),
        )

        if str(self.path) == "/stats":
            # TODO: Get stats
            self.send_success(
                {
                    "all": {"solved": 2, "validations": 1234567},
                    "nodes": [
                        {"address": "127.0.0.1:7000", "validations": 1000000},
                        {"address": "127.0.0.1:7001", "validations": 234567},
                    ],
                }
            )

        elif str(self.path) == "/network":
            # TODO: Get network
            self.send_success({"children": ""})

        elif str(self.path) == "/solve":
            self.set_error("GET method not allowed for /solve")
        else:
            self.set_error(f"Path {self.path} not available")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        body = json.loads(post_data.decode("utf-8"))

        logging.info(
            "POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
            str(self.path),
            str(self.headers),
            body,
        )

        # TODO: Solve sudoku
        self.send_success(body["sudoku"])


def run_http_server(
    port: int, p2p_server: P2PServer
) -> Generator[HTTPServer, Any, None]:
    logging.basicConfig(level=logging.INFO)
    server_address: Address = ("", port)
    httpd = HTTPServer(
        server_address,
        lambda *args, **kwargs: SudokuHTTPHandler(
            *args, p2p_server=p2p_server, **kwargs
        ),
    )
    logging.info(f"Starting HTTP on port {port}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")
