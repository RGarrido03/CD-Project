import copy
import json
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
    SudokuSolved,
    StoreSudoku,
    P2PProtocolBadFormat,
)
from sudoku import Sudoku


class P2PServer:
    def __init__(self, port: int, parent: Optional[str], handicap: float):
        self.address = (socket.gethostbyname_ex(socket.gethostname())[2][-1], port)
        self.handicap = handicap
        self.solved: int = 0  # Global state across the network
        self.validations: int = 0  # Node-only state
        self.parent = parent
        logging.basicConfig(encoding="utf-8", level=logging.DEBUG)

        # sudokus        -> {id: (grid: Sudoku, jobs: jobs_structure, address: Address)}
        # jobs_structure -> [(complete: JobStatus, assigned_node: Address)]
        self.sudokus: dict[str, tuple[Sudoku, jobs_structure, Address, sudoku_type]] = (
            {}
        )

        # {node_addr: Address: (socket: socket.socket, validations: int, timeout: float)}
        self.neighbors: dict[Address, tuple[socket.socket, int, float]] = {}

        # {old_squares: new_squares}
        self.squares_history: dict[json, sudoku_type | None] = {}

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("", self.address[1]))
        self.socket.setblocking(False)
        self.socket.listen(1000)

        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, self.accept)

    def connect_to_node(self, addr: Address, parent: bool = False):
        wait = 1
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(addr)
                self.sel.register(sock, selectors.EVENT_READ, self.read)
                self.neighbors[addr] = (sock, 0, time.time())
                message = (
                    JoinParent(self.address) if parent else JoinOther(self.address)
                )
                P2PProtocol.send_msg(sock, message)
                break
            except ConnectionRefusedError:
                logging.error(
                    f"Failed to connect to {AddressUtils.address_to_str(addr)}. Retrying in {wait * 2}s"
                )
                time.sleep(wait := wait * 2)

    def get_stats(self) -> dict[str, Any]:
        validations = (
            sum([v for (_, v, __) in self.neighbors.values()]) + self.validations
        )
        nodes = [
            {"address": ":".join(str(prop) for prop in k), "validations": v[1]}
            for (k, v) in self.neighbors.items()
        ]
        nodes.insert(
            0,
            {
                "address": AddressUtils.address_to_str(self.address),
                "validations": self.validations,
            },
        )

        return {
            "all": {
                "solved": self.solved,
                "validations": validations,
            },
            "nodes": nodes,
        }

    def get_network(self) -> dict[str, list]:
        all_network = list(self.neighbors.keys()) + [self.address]
        return {
            AddressUtils.address_to_str(node): [
                AddressUtils.address_to_str(i) for i in all_network if i != node
            ]
            for node in all_network
        }

    async def solve_sudoku(self, grid: sudoku_type):
        if grid in [s[3] for s in self.sudokus.values()]:
            logging.info(f"Grid already solved: {grid}")
            solved_grid = [s[3] for s in self.sudokus.values() if s[3] == grid][0]
            return solved_grid

        _id = str(uuid.uuid4())
        sudoku = Sudoku(grid)
        self.sudokus[_id] = (
            sudoku,
            [(JobStatus.PENDING, None) for _ in range(0, 9)],
            self.address,
            copy.deepcopy(sudoku.grid),
        )

        for sock in [n[0] for n in self.neighbors.values()]:
            P2PProtocol.send_msg(
                sock,
                StoreSudoku(_id, grid, self.address),
            )

        return await self.distribute_work(_id)

    def accept(self, sock: socket.socket):
        conn, _ = sock.accept()
        conn.setblocking(False)
        conn.settimeout(3)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def disconnect_node(self, conn: socket.socket):
        addr = self.get_address_from_socket(conn)
        logging.warning(f"Node {AddressUtils.address_to_str(addr)} has disconnected")
        self.sel.unregister(conn)
        conn.close()
        self.cancel_disconnecting_node_jobs(addr)
        self.neighbors = {k: v for (k, v) in self.neighbors.items() if v[0] != conn}

    def read(self, conn: socket.socket):
        try:
            data = P2PProtocol.recv_msg(conn)
        except P2PProtocolBadFormat:
            logging.error(f"Bad format from {self.get_address_from_socket(conn)}")
            self.disconnect_node(conn)
            return

        if data is None:
            self.disconnect_node(conn)
            return

        if not isinstance(data, KeepAlive):
            logging.info(
                "Received %s at %s: %s",
                type(data).__name__,
                datetime.now().time().replace(microsecond=0).isoformat(),
                data,
            )

        if isinstance(data, JoinParent):
            neighbors = list(self.neighbors.keys())
            message = JoinParentResponse(neighbors)
            self.neighbors[data.address] = (conn, 0, time.time())
            P2PProtocol.send_msg(conn, message)
            logging.info("Sent %s to %s", message, data.address)
        elif isinstance(data, JoinParentResponse):
            for node in data.nodes:
                self.connect_to_node(node)
        elif isinstance(data, StoreSudoku):
            self.sudokus[data.id] = (
                Sudoku(data.grid),
                [(JobStatus.PENDING, None) for _ in range(0, 9)],
                data.address,
                data.grid,
            )
        elif isinstance(data, JoinOther):
            message = JoinOtherResponse(self.solved, self.validations)
            self.neighbors[data.address] = (conn, 0, time.time())
            P2PProtocol.send_msg(conn, message)
            logging.info("Sent %s to %s", message, data.address)
        elif isinstance(data, JoinOtherResponse):
            self.neighbors[self.get_address_from_socket(conn)] = (
                conn,
                data.validations,
                time.time(),
            )
        elif isinstance(data, KeepAlive):
            self.neighbors[self.get_address_from_socket(conn)] = (
                conn,
                self.neighbors[self.get_address_from_socket(conn)][1],
                time.time(),
            )
        elif isinstance(data, WorkRequest):
            threading.Thread(
                target=self.handle_work_request, args=(conn, data), daemon=True
            ).start()
        elif isinstance(data, WorkAck):
            # TODO: Implement this. A job data structure is yet to be created.
            pass
        elif isinstance(data, WorkComplete):
            self.handle_work_complete(conn, data)
        elif isinstance(data, SudokuSolved):
            self.solved += 1
            logging.info(
                f"Sudoku {data.id} solved by {self.get_address_from_socket(conn)}"
            )
            self.sudokus[data.id] = (
                data.sudoku,
                [(JobStatus.COMPLETED, None) for _ in range(0, 9)],
                self.get_address_from_socket(conn),
                self.sudokus[data.id][3],
            )
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
            self.sudokus[data.id][3],
        )
        P2PProtocol.send_msg(conn, WorkAck(data.id, data.job))

        changing_grid = data.sudoku.grid
        number_of_zeros = Sudoku.get_number_of_zeros_in_square(data.job, changing_grid)

        while True:
            if grid_from_upstream != self.sudokus[data.id][0].grid:
                logging.warning(f"Work {data.job} canceled")
                return

            changing_grid, completed = Sudoku.update_square(data.job, changing_grid)
            self.validations = self.validations + 1

            time.sleep(self.handicap / (number_of_zeros + 1))

            if completed:
                self.sudokus[data.id][1][data.job] = (
                    JobStatus.COMPLETED,
                    self.sudokus[data.id][1][data.job][1],
                )
                self.sudokus[data.id][0].grid = changing_grid
                break

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

        self.neighbors[addr] = (self.neighbors[addr][0], data.validations, time.time())

        self.update_sudoku_with_new_values(data.id, data.sudoku.grid, data.job)
        self.sudokus[data.id][1][data.job] = (
            JobStatus.COMPLETED,
            self.sudokus[data.id][1][data.job][1],
        )

    async def distribute_work(self, sudoku_id: str):
        (grid, jobs, _, _) = self.sudokus[sudoku_id]

        copy_grid = copy.deepcopy(grid.grid)

        while not self.is_sudoku_completed(sudoku_id):
            time.sleep(0.1)
            logging.debug(f"Jobs: {jobs}")
            zeros_per_square = [
                (i, Sudoku.get_number_of_zeros_in_square(i, grid.grid))
                for i in range(9)
            ]
            zeros_per_square.sort(key=lambda x: x[1])

            for square, zeros in zeros_per_square:
                job = self.sudokus[sudoku_id][1][square]

                if zeros == 0:
                    if job[0] != JobStatus.COMPLETED:
                        self.sudokus[sudoku_id][1][square] = (
                            JobStatus.COMPLETED,
                            self.sudokus[sudoku_id][1][square][1],
                        )
                    continue

                squares = Sudoku.return_square(square, grid.grid)
                logging.info(f"History: {self.squares_history}, and squares: {squares}")
                if str(squares) in self.squares_history:
                    logging.info(f"Square {square} already solved")
                    logging.info(
                        f"Replacing square {square} with {self.squares_history[str(squares)]}"
                    )
                    solved_square: list[list[int]] = json.loads(str(squares))
                    Sudoku.replace_square(square, solved_square, grid.grid)
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

        logging.info(f"{sudoku_id} solved: {self.sudokus[sudoku_id][0]}")
        for square in range(9):
            squares = Sudoku.return_square(square, copy_grid)
            self.squares_history[json.dumps(squares)] = Sudoku.return_square(
                square, grid.grid
            )
        if not self.sudokus[sudoku_id][0].check():
            return None

        self.solved += 1
        for sock in [n[0] for n in self.neighbors.values()]:
            P2PProtocol.send_msg(
                sock,
                SudokuSolved(sudoku_id, self.sudokus[sudoku_id][0], self.address),
            )
        return self.sudokus[sudoku_id][0].grid

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

    def cancel_disconnecting_node_jobs(self, addr: Address):
        for id, sudoku in self.sudokus.items():
            for i, job in enumerate(sudoku[1]):
                if job[0] == JobStatus.IN_PROGRESS and job[1] == addr:
                    self.sudokus[id][1][i] = (JobStatus.PENDING, addr)

    def is_sudoku_completed(self, id: str):
        return all([job[0] == JobStatus.COMPLETED for job in self.sudokus[id][1]])

    def update_sudoku_with_new_values(
        self, sudoku_id: str, new_grid: sudoku_type, job: int
    ):
        rows_idx = [i + ((job // 3) * 3) for i in range(3)]
        cols_idx = [i + ((job % 3) * 3) for i in range(3)]

        for row in rows_idx:
            for col in cols_idx:
                self.sudokus[sudoku_id][0].grid[row][col] = new_grid[row][col]

    def send_keep_alive_to_neighbors(self):
        while True:
            time.sleep(1)
            for sock in [n[0] for n in self.neighbors.values()]:
                P2PProtocol.send_msg(sock, KeepAlive())

    def check_keep_alive_from_neighbors(self):
        while True:
            current = time.time()
            for addr, (conn, _, last_beat) in self.neighbors.items():
                if current - last_beat > 3:
                    logging.warning(
                        f"Node {AddressUtils.address_to_str(addr)} is dead. Disconnecting..."
                    )
                    self.disconnect_node(conn)

    def run(self):
        threading.Thread(target=self.send_keep_alive_to_neighbors, daemon=True).start()
        threading.Thread(
            target=self.check_keep_alive_from_neighbors, daemon=True
        ).start()

        if self.parent is not None:
            self.connect_to_node(AddressUtils.str_to_address(self.parent), parent=True)

        while True:
            events = self.sel.select()
            for key, _ in events:
                callback = key.data
                callback(key.fileobj)
