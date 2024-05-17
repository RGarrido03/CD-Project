import argparse
import threading

from network import run_http_server
from p2p import run_p2p_server


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

    http_thread = threading.Thread(target=run_http_server, args=(args.port,))
    http_thread.start()

    p2p_thread = threading.Thread(target=run_p2p_server, args=(args.service, args.address, args.handicap))
    p2p_thread.start()


if __name__ == "__main__":
    main()
