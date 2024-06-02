import selectors
import socket
from typing import Optional

from custom_types import Address
from protocol import P2PProtocol, JoinParent, JoinParentResponse


class P2PServer:
    def __init__(self, port: int, parent: Optional[str], handicap: int):
        self.port = port
        self.handicap = handicap

        """
        Neighbors is a dictionary with the address (host, port) as the key,
        and a tuple (socket, all, validations) as the value.
        """
        self.neighbors: dict[Address, tuple[socket.socket, int, int]] = {}

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("127.0.0.1", self.port))
        self.socket.setblocking(False)
        self.socket.listen(1000)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

        if parent is not None:
            (addr, port) = parent.split(":")
            self.connect_to_node(addr, int(port))

    def connect_to_node(self, addr: str, port: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.neighbors[(addr, port)] = (sock, 0, 0)
        sock.setblocking(False)
        sock.connect((addr, int(port)))

    def get_all_stats(self) -> tuple[int, int]:
        return sum([s[0] for (_, s) in self.neighbors.items()]), sum(
            [s[1] for (_, s) in self.neighbors.items()]
        )

    def add_stats_to_neighbor(self, conn: Address, stats: tuple[int, int]) -> None:
        (sock, all, validations) = self.neighbors[conn]
        self.neighbors[conn] = (sock, all + stats[0], validations + stats[1])

    def accept(self, sock: socket.socket):
        conn, addr = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.neighbors[addr] = (conn, 0, 0)

    def read(self, conn: socket.socket):
        data = P2PProtocol.recv_msg(conn)

        if data is None:
            self.sel.unregister(conn)
            conn.close()
            del self.neighbors[conn.getsockname()]
            return

        print(data)
        # TODO: Take actions

    def run(self):
        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)


# falta comunicarem entre si (connect com socket ou algo do genero) e meter o network (implementar os nos a
# funcionar entre si - connectados. Cada nó vai perguntar aos seus filhos. Parent é aquele que tu connectas e dás
# endereço na linha de comandos) e status a funcionar.
def run_p2p_server(port: int, address: Optional[str], handicap: int) -> P2PServer:
    p2p_server = P2PServer(port, address, handicap)
    yield p2p_server
    p2p_server.run()
