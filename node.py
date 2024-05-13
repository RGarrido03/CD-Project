import argparse


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
    print(args.port, args.service, args.address, args.handicap)


if __name__ == "__main__":
    main()
