import logging
import selectors
import socket
import uuid
from datetime import datetime
from typing import Optional, Any

from consts import JobStatus
from custom_types import Address, sudoku_type, jobs_structure
from utils import AddressUtils
from protocol import (
    P2PProtocol,
    JoinParent,
    JoinParentResponse,
    JoinOther,
    JoinOtherResponse,
    KeepAlive,
    WorkRequest,
    WorkAck,
    WorkComplete,
    WorkCancel,
    WorkCancelAck,
)
from sudoku import Sudoku


def send_work_request(sudoku_id, node):
    print("Work request sent to node: ", node)


class P2PServer:
    def __init__(self, port: int, parent: Optional[str], handicap: int):
        self.address = (socket.gethostbyname(socket.gethostname()), port)
        self.handicap = handicap
        self.solved: int = 0
        self.validations: int = 0
        self.parent = parent

        # sudokus        -> {id: (grid: Sudoku, complete: bool, jobs: jobs_structure, address: Address)}
        # jobs_structure -> [(complete: JobStatus, assigned_node: Address)]. List index is the square number.
        self.sudokus: dict[str, tuple[Sudoku, bool, jobs_structure, Address]] = {}

        # {node_addr: Address: (socket: socket.socket, solved: int, validations: int)}
        self.neighbors: dict[Address, tuple[socket.socket, int, int]] = {}

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("", self.address[1]))
        self.socket.setblocking(False)
        self.socket.listen(1000)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

    def connect_to_node(self, addr: Address, parent: bool = False):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.neighbors[addr] = (sock, 0, 0)
        # TODO: Timeout
        sock.connect(addr)
        self.sel.register(sock, selectors.EVENT_READ, self.read)

        message = JoinParent(self.address) if parent else JoinOther(self.address)
        P2PProtocol.send_msg(sock, message)

    def get_stats(self) -> dict[str, Any]:
        return {
            "all": {
                "solved": sum([s[1] for (_, s) in self.neighbors.items()]),
                "validations": sum([s[2] for (_, s) in self.neighbors.items()]),
            },
            "nodes": [
                {"address": ":".join(str(prop) for prop in k), "validations": v[2]}
                for (k, v) in self.neighbors.items()
            ],
        }

    def add_stats_to_neighbor(self, conn: Address, stats: tuple[int, int]) -> None:
        (sock, solved, validations) = self.neighbors[conn]
        self.neighbors[conn] = (sock, solved + stats[0], validations + stats[1])

    def get_network(self) -> dict[str, list]:
        all_network = list(self.neighbors.keys()) + [self.address]
        return {
            AddressUtils.address_to_str(node): [
                AddressUtils.address_to_str(i) for i in all_network if i != node
            ]
            for node in all_network
        }

    def solve_sudoku(self, grid: sudoku_type) -> sudoku_type:
        # TODO: Cache (both full and per-square)
        _id = str(uuid.uuid4())
        sudoku = Sudoku(grid)
        self.sudokus[_id] = (
            sudoku,
            False,
            [(JobStatus.PENDING, None) for _ in range(0, 9)],
        )
        self.distribute_work(_id)
        return sudoku.grid

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn: socket.socket):
        data = P2PProtocol.recv_msg(conn)

        if data is None:
            self.sel.unregister(conn)
            conn.close()
            self.neighbors = {k: v for (k, v) in self.neighbors.items() if v[0] != conn}
            return

        logging.info(
            "Received %s at %s: %s",
            type(data).__name__,
            datetime.now().time().replace(microsecond=0).isoformat(),
            data,
        )

        if isinstance(data, JoinParent):
            neighbors = list(self.neighbors.keys())
            message = JoinParentResponse(neighbors)
            self.neighbors[data.address] = (conn, 0, 0)
            P2PProtocol.send_msg(conn, message)
            logging.info("Sent %s to %s", message, data.address)
        elif isinstance(data, JoinParentResponse):
            for node in data.nodes:
                self.connect_to_node(node)
        elif isinstance(data, JoinOther):
            message = JoinOtherResponse(self.solved, self.validations)
            self.neighbors[data.address] = (conn, 0, 0)
            P2PProtocol.send_msg(conn, message)
        elif isinstance(data, JoinOtherResponse):
            self.neighbors[conn.getsockname()] = (conn, data.solved, data.validations)
        elif isinstance(data, KeepAlive):
            # TODO: Is this needed?
            pass
        elif isinstance(data, WorkRequest):
            self.handle_work_request(data)
        elif isinstance(data, WorkAck):
            # TODO: Implement this. A job data structure is yet to be created.
            pass
        elif isinstance(data, WorkComplete):
            self.handle_work_complete(conn, data)
        elif isinstance(data, WorkCancel):
            self.handle_work_cancel(conn, data)
        elif isinstance(data, WorkCancelAck):
            self.handle_work_cancel_ack(conn, data)
        else:
            print("Unsupported message", data)

    def distribute_work(self, sudoku_id: str):
        (grid, complete, jobs) = self.sudokus[sudoku_id]
        number_of_nodes = len(self.get_network())
        number_of_progress_nodes = 0
        number_of_completed_nodes = 0

        while not complete:
            for square in range(9):
                if (
                    jobs[square][0] == JobStatus.PENDING
                    and number_of_progress_nodes < number_of_nodes
                ):
                    send_work_request(sudoku_id, square)
                    number_of_progress_nodes += 1
                    jobs[square] = (JobStatus.IN_PROGRESS, self.address)
                elif jobs[square][0] == JobStatus.IN_PROGRESS:
                    jobs[square] = (JobStatus.COMPLETED, jobs[square][1])
                    print("Job completed by node: ", jobs[square][1])
                    number_of_progress_nodes -= 1
                elif jobs[square][0] == JobStatus.COMPLETED:
                    jobs[square] = (JobStatus.COMPLETED, jobs[square][1])
                    number_of_completed_nodes += 1
                    if number_of_completed_nodes == 9:
                        complete = True
                        print("Jobs done!")
                print("jobs: ", jobs)

    def run(self):
        if self.parent is not None:
            self.connect_to_node(AddressUtils.str_to_address(self.parent), parent=True)

        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)
