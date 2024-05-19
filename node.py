import argparse
import threading

from network import run_http_server
from p2p import run_p2p_server


class Node:
    def __init__(self, http_port: int, p2p_port, address: str, handicap: int):
        self.http_port = http_port
        self.p2p_port = p2p_port
        self.address = address
        self.handicap = handicap
        self.solved = 0
        self.validations = 0

        self.http_thread = threading.Thread(target=run_http_server, args=(http_port,))
        self.http_thread.start()

        self.p2p_thread = threading.Thread(
            target=run_p2p_server, args=(p2p_port, address, handicap)
        )
        self.p2p_thread.start()


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
        default="127.0.0.1:7000",
    )
    parser.add_argument("-h", "--handicap", help="Handicap", type=int, default=0)
    args = parser.parse_args()

    Node(args.port, args.service, args.address, args.handicap)


if __name__ == "__main__":
    main()
