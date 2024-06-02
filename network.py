import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
import logging

from custom_types import Address
from p2p import P2PServer


class SudokuHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, p2p_server: P2PServer, *args):
        self.p2p_server: P2PServer = p2p_server
        super().__init__(*args)

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
        logging.info("GET %s, from %s", self.path, self.headers.get("Host"))

        if str(self.path) == "/stats":
            self.send_success(self.p2p_server.get_stats())

        elif str(self.path) == "/network":
            self.send_success(self.p2p_server.get_network())

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

        self.send_success({"sudoku": self.p2p_server.solve_sudoku(body["sudoku"])})


def run_http_server(port: int, p2p_server: P2PServer):
    logging.basicConfig(level=logging.INFO)
    server_address: Address = ("", port)

    def handler(*args) -> SudokuHTTPHandler:
        return SudokuHTTPHandler(p2p_server, *args)

    httpd = HTTPServer(server_address, handler)
    logging.info(f"Starting HTTP on port {port}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")
