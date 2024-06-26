import argparse
import threading
from typing import Optional

from network import run_http_server
from p2p import P2PServer


class Node:
    def __init__(
        self, http_port: int, p2p_port: int, address: Optional[str], handicap: int
    ):
        self.http_port = http_port
        self.p2p = P2PServer(p2p_port, address, handicap / 1000)

        self.http_thread = threading.Thread(
            target=run_http_server, args=(http_port, self.p2p), daemon=True
        )

    def run(self):
        try:
            self.http_thread.start()
            self.p2p.run()
        except KeyboardInterrupt:
            self.p2p.socket.close()


def main():
    parser = argparse.ArgumentParser(conflict_handler="resolve")
    parser.add_argument("-p", "--port", help="Node's HTTP Port", type=int, default=8000)
    parser.add_argument(
        "-s", "--service", help="Node's P2P Port", type=int, default=7000
    )
    parser.add_argument(
        "-a",
        "--address",
        help="P2P network's address",
        type=str,
    )
    parser.add_argument("-h", "--handicap", help="Handicap", type=int, default=0)
    args = parser.parse_args()

    node = Node(args.port, args.service, args.address, args.handicap)
    node.run()


if __name__ == "__main__":
    main()
