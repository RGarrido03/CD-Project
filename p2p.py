import selectors
import socket
from typing import Optional

from custom_types import Address
from protocol import P2PProtocol


class P2PServer:
    def __init__(self, port: int, parent: Optional[Address], handicap: int):
        self.port = port
        self.parent = parent
        self.handicap = handicap
        self.children: list[socket.socket] = []

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", self.port))
        self.socket.setblocking(False)
        self.socket.listen(1000)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.children.append(conn)

    def read(self, conn: socket.socket):
        data = P2PProtocol.recv_msg(conn)

        if data is None:
            self.sel.unregister(conn)
            conn.close()
            self.children.remove(conn)
            return

        print(data)
        # TODO: Take actions

    def run(self):
        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)

# falta comunicarem entre si (connect com socket ou algo do genero) e meter o network (implementar os nos a funcionar
# entre si - connectados. Cada nó vai perguntar aos seus filhos. Parent é aquele que tu connectas e dás endereço na
# linha de comandos) e status a funcionar.
def run_p2p_server(port: int, address: Optional[str], handicap: int):
    if address is not None:
        for addr in address.split(","):
            host, port = addr.split(":")
            port = int(port)
            print(f"Connected to {host}:{port}\n")
            p2p_server = P2PServer(port, (host, port), handicap)
            p2p_server.run()
    p2p_server = P2PServer(port, address, handicap)
    p2p_server.run()
