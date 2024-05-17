import selectors
import socket

from custom_types import Address


class P2PServer:
    def __init__(self, port: int, parent: Address, handicap: int):
        self.port = port
        self.parent = parent
        self.handicap = handicap
        self.connections = []

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", self.port))
        self.socket.setblocking(False)
        self.socket.listen(5)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.connections.append(conn)

    def read(self, conn: socket.socket):
        # TODO: Implement read, abstract by using protocol
        data = conn.recv(1024)
        if not data:
            self.sel.unregister(conn)
            conn.close()
            self.connections.remove(conn)
            return

        print(data)

    def run(self):
        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)


def run_p2p_server(port: int, address: str, handicap: int):
    a = address.split(":")
    address = (a[0], int(a[1]))
    p2p_server = P2PServer(port, address, handicap)
    p2p_server.run()
