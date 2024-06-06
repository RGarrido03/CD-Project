import logging
import selectors
import socket
import threading
import time
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

# TODO: Fix solved number


class P2PServer:
    def __init__(self, port: int, parent: Optional[str], handicap: float):
        self.address = (socket.gethostbyname(socket.gethostname()), port)
        self.handicap = handicap
        self.solved: int = 0
        self.validations: int = 0
        self.parent = parent

        # sudokus        -> {id: (grid: Sudoku, jobs: jobs_structure, address: Address)}
        # jobs_structure -> [(complete: JobStatus, assigned_node: Address)]
        self.sudokus: dict[str, tuple[Sudoku, jobs_structure, Address]] = {}

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

    async def solve_sudoku(self, grid: sudoku_type) -> sudoku_type:
        # TODO: Cache (both full and per-square)
        _id = str(uuid.uuid4())
        sudoku = Sudoku(grid)
        self.sudokus[_id] = (
            sudoku,
            [(JobStatus.PENDING, None) for _ in range(0, 9)],
            self.address,
        )
        return await self.distribute_work(_id)

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn: socket.socket):
        data = P2PProtocol.recv_msg(conn)

        if data is None:
            logging.warning(
                f"Node {AddressUtils.address_to_str(self.get_address_from_socket(conn))} has disconnected"
            )
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
            logging.info("Sent %s to %s", message, data.address)
        elif isinstance(data, JoinOtherResponse):
            self.neighbors[conn.getsockname()] = (conn, data.solved, data.validations)
        elif isinstance(data, KeepAlive):
            # TODO: Is this needed?
            pass
        elif isinstance(data, WorkRequest):
            threading.Thread(
                target=self.handle_work_request, args=(conn, data), daemon=True
            ).start()
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

    def handle_work_request(self, conn: socket.socket, data: WorkRequest):
        grid_from_upstream = data.sudoku.grid
        addr = self.get_address_from_socket(conn)

        logging.info(
            f"Handling work {data.job} from {addr} with grid\n{data.sudoku}\nand jobs {data.jobs}"
        )

        self.sudokus[data.id] = (
            data.sudoku,
            data.jobs,
            self.get_address_from_socket(conn),
        )
        P2PProtocol.send_msg(conn, WorkAck(data.id, data.job))

        changing_grid = data.sudoku.grid

        while True:
            if grid_from_upstream != self.sudokus[data.id][0].grid:
                return

            changing_grid, completed = Sudoku.update_square(data.job, changing_grid)
            self.validations = self.validations + 1

            if completed:
                self.sudokus[data.id][1][data.job] = (
                    JobStatus.COMPLETED,
                    self.sudokus[data.id][1][data.job][1],
                )
                self.sudokus[data.id][0].grid = changing_grid
                break

        time.sleep(self.handicap)

        logging.info(
            f"Finished work {data.job} from {addr} with grid\n{self.sudokus[data.id][0]}"
        )

        for sock in [n[0] for n in self.neighbors.values()]:
            P2PProtocol.send_msg(
                sock,
                WorkComplete(
                    data.id, self.sudokus[data.id][0], data.job, self.validations
                ),
            )

    def handle_work_complete(self, conn: socket.socket, data: WorkComplete):
        addr = self.get_address_from_socket(conn)

        logging.info(
            f"Received complete work {data.job} from {addr} with grid\n{data.sudoku}"
        )

        self.neighbors[addr] = (self.neighbors[addr][0], data.validations, 0)
        self.sudokus[data.id] = (
            data.sudoku,
            self.sudokus[data.id][1],
            self.sudokus[data.id][2],
        )

    async def distribute_work(self, sudoku_id: str):
        new_grid = []
        (grid, jobs, _) = self.sudokus[sudoku_id]

        while not self.is_sudoku_completed(sudoku_id):
            time.sleep(0.2)  # TODO: Remove this

            for square in range(9):
                job = self.sudokus[sudoku_id][1][square]

                if (
                    job[0] == JobStatus.PENDING
                    and len(self.get_addresses_of_free_nodes(sudoku_id)) != 0
                ):
                    node = self.get_addresses_of_free_nodes(sudoku_id)[0]

                    logging.info(f"Sending job {square} to {node} with grid\n{grid}")

                    self.sudokus[sudoku_id][1][square] = (
                        JobStatus.IN_PROGRESS,
                        node,
                    )
                    P2PProtocol.send_msg(
                        self.neighbors[node][0],
                        WorkRequest(
                            sudoku_id,
                            grid,
                            self.sudokus[sudoku_id][1],
                            square,
                        ),
                    )
                    break

        logging.info(f"{sudoku_id} solved: {new_grid}")
        return new_grid

    def get_addresses_of_free_nodes(self, sudoku_id: str) -> list[Address]:
        return list(
            set(self.neighbors.keys())
            - set(
                [
                    job[1]
                    for job in self.sudokus[sudoku_id][1]
                    if job[0] == JobStatus.IN_PROGRESS
                ]
            )
        )

    def get_address_from_executed_nodes(self, sudoku_id: str):
        return [
            job[1] for job in self.sudokus[sudoku_id][1] if job[0] == JobStatus.PENDING
        ]

    def get_address_from_socket(self, conn: socket.socket) -> Address:
        return [k for (k, v) in self.neighbors.items() if v[0] == conn][0]

    def is_sudoku_completed(self, id: str):
        return all([job[0] == JobStatus.COMPLETED for job in self.sudokus[id][1]])

    def run(self):
        if self.parent is not None:
            self.connect_to_node(AddressUtils.str_to_address(self.parent), parent=True)

        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)
