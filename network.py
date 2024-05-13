import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging


class S(BaseHTTPRequestHandler):
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
            "GET request,\nsolve: %s\nstats:\n%snetwork\n",
            str(self.path),
            str(self.headers),
        )

        if str(self.path) == "/stats":
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
            self.send_success(
                {
                    "192.168.1.100:7000": [
                        "192.168.1.100:7001",
                        "192.168.1.100:7002",
                    ],
                    "192.168.1.100:7001": ["192.168.1.100:7000"],
                    "192.168.1.100:7002": [
                        "192.168.1.100:7000",
                        "192.168.1.11:7003",
                    ],
                    "192.168.1.11:7003": ["192.168.1.100:7002"],
                }
            )

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
        self.send_success(body)


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logging.info("Starting httpd...\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")


if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
