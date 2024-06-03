import logging
import selectors
import socket
import uuid
from datetime import datetime
from typing import Optional, Any

from consts import JobStatus
from custom_types import Address, sudoku_type, jobs_structure
from gen import solve_sudoku
from utils import subdivide_board, AddressUtils
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


class P2PServer:
    def __init__(self, port: int, parent: Optional[str], handicap: int):
        self.address = (socket.gethostbyname(socket.gethostname()), port)
        self.handicap = handicap
        self.solved: int = 0
        self.validations: int = 0
        self.parent = parent

        # sudokus        -> {id: (grid: Sudoku, complete: bool, jobs: jobs_structure)}
        # jobs_structure -> [(complete: JobStatus, assigned_node: Address)]. List index is the square number.
        self.sudokus: dict[str, tuple[Sudoku, bool, jobs_structure]] = {}

        # {node_addr: Address: (socket: socket.socket, solved: int, validations: int)}
        self.neighbors: dict[Address, tuple[socket.socket, int, int]] = {}

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.address)
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
        (sock, all, validations) = self.neighbors[conn]
        self.neighbors[conn] = (sock, all + stats[0], validations + stats[1])

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

    def distribute_work(self, board):
        """Distribute the 3x3 squares to different nodes."""
        squares = subdivide_board(board)
        for idx, square in enumerate(squares):
            work_request_id = str(
                uuid.uuid4()
            )  # gerar um id???? foi o grande P que me recomendou
            message = WorkRequest(
                work_request_id, square, self.socket.getsockname(), idx
            )
            self.jobs[work_request_id] = (square, idx)
            neighbor_addr = list(self.neighbors.keys())[idx % len(self.neighbors)]
            P2PProtocol.send_msg(self.neighbors[neighbor_addr][0], message)

    def handle_work_request(self, data: WorkRequest):
        print(f"Handling work request: {data.id}")
        board = [[0] * 9 for _ in range(9)]
        start_row, start_col = 3 * (data.idx // 3), 3 * (data.idx % 3)
        for i in range(3):
            for j in range(3):
                board[start_row + i][start_col + j] = data.board[i][j]

        sudoku = Sudoku(board)
        solved = solve_sudoku(sudoku.grid)

        if solved:
            message = WorkComplete(
                data.id, board[start_row : start_row + 3], validations=1, idx=data.idx
            )
        else:
            message = WorkCancel(data.id)

        P2PProtocol.send_msg(self.neighbors[data.address][0], message)

    def handle_work_complete(self, conn: socket.socket, data: WorkComplete):
        print(f"Work complete for job: {data.id}")
        if data.id in self.jobs:
            _, idx = self.jobs[data.id]
            start_row, start_col = 3 * (idx // 3), 3 * (idx % 3)
            for i in range(3):
                for j in range(3):
                    self.board[start_row + i][start_col + j] = data.board[i][j]

            del self.jobs[data.id]  # remove o job da lista de jobs com del :D
            if len(self.jobs) == 0:
                print("All jobs are complete.")
                if Sudoku(self.board).check():
                    print("Sudoku solved correctly!")
                else:
                    print("There was an error in the solution.")
        else:
            print(f"Invalid or unknown job ID: {data.id}")

    def handle_work_cancel(self, conn: socket.socket, data: WorkCancel):
        print(f"Work cancelled for job: {data.id}")
        message = WorkCancelAck(data.id, self.validations)
        P2PProtocol.send_msg(conn, message)

    def handle_work_cancel_ack(self, conn: socket.socket, data: WorkCancelAck):
        print(f"Work cancel acknowledged for job: {data.id}")
        solved = self.neighbors[conn.getsockname()][1]
        validations = self.neighbors[conn.getsockname()][2] + data.validations
        self.neighbors[conn.getsockname()] = (conn, solved, validations)

    def run(self):
        if self.parent is not None:
            self.connect_to_node(AddressUtils.str_to_address(self.parent), parent=True)

        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)
