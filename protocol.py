import pickle
from abc import ABC
from enum import Enum
from socket import socket
from typing import Optional

from consts import Command
from custom_types import Address, jobs_structure, sudoku_type
from sudoku import Sudoku


class Message(ABC):
    """
    Base class for all protocol messages.

    :param command: Message type.
    :type command: Command
    """

    def __init__(self, command: Command):
        self.command = command

    def to_dict(self) -> dict[str, str]:
        return {
            k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()
        }

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return self.__str__()


class StoreSudoku(Message):
    """
    Store the Sudoku in the node

    :param id: Sudoku UUID.
    :type id: str
    :param grid: Sudoku grid.
    :type grid: sudoku_type
    :param address: Address of node
    :type address: Address
    """

    def __init__(self, id: str, grid: sudoku_type, address: Address):
        super().__init__(Command.STORE_SUDOKU)
        self.id = id
        self.grid = grid
        self.address = address


class JoinParent(Message):
    """
    When the node is created and a parent is specified,
    send a request to that parent, to get the list of all nodes in the network.
    """

    def __init__(self, address: Address):
        super().__init__(Command.JOIN_PARENT)
        self.address = address


class JoinParentResponse(Message):
    """
    Response to the JoinParent message.
    It contains the list of all nodes in the network.

    :param nodes: List of all nodes in the network.
    :type nodes: list[Address]
    """

    def __init__(self, nodes: list[Address]):
        super().__init__(Command.JOIN_PARENT_RESPONSE)
        self.nodes: list[Address] = nodes


class JoinOther(Message):
    """
    After getting the nodes list from the parent (JoinParentResponse message),
    send this message to each one of them, to get their stats.
    """

    def __init__(self, address: Address):
        super().__init__(Command.JOIN_OTHER)
        self.address = address


class JoinOtherResponse(Message):
    """
    Response to the JoinOther message.
    It contains the node's stats: solved puzzles and number of validations.

    :param solved: Number of solved puzzles.
    :type solved: int
    :param validations: Number of validations.
    :type validations: int
    """

    def __init__(self, solved: int, validations: int):
        super().__init__(Command.JOIN_OTHER_RESPONSE)
        self.solved = solved
        self.validations = validations


class KeepAlive(Message):
    """
    Ping message.
    Probably to be used in a scheduled timing.
    """

    def __init__(self):
        super().__init__(Command.KEEP_ALIVE)


class WorkRequest(Message):
    """
    Send a work job to a node.
    Probably this will have some changes when we define the algorithm.

    :param id: Job UUID.
    :type id: str
    :param sudoku: Sudoku object.
    :type sudoku: Sudoku
    :param jobs: Current jobs status for the related sudoku
    :type jobs: jobs_structure
    :param job: Job (aka square) number.
    :type job: int
    """

    def __init__(self, id: str, sudoku: Sudoku, jobs: jobs_structure, job: int):
        super().__init__(Command.WORK_REQUEST)
        self.id = id
        self.sudoku = sudoku
        self.jobs = jobs
        self.job = job


class WorkAck(Message):
    """
    Acknowledge WorkRequest message.

    :param id: Sudoku UUID.
    :type id: str
    :param job: Job (aka square) number.
    :type job: int
    """

    def __init__(self, id: str, job: int):
        super().__init__(Command.WORK_ACK)
        self.id = id
        self.job = job


class WorkComplete(Message):
    """
    The job is complete.
    This message may be sent to all nodes (or just the one who requested? Let's see)

    It includes the number of validations, for updating the stats.
    Only validations are needed, the solved number is implicitly +1.

    :param id: Job UUID.
    :type id: str
    :param sudoku: Sudoku object.
    :type sudoku: Sudoku
    :param job: Job (aka square) number.
    :type job: int
    :param validations: Number of validations.
    :type validations: int
    """

    def __init__(self, id: str, sudoku: Sudoku, job: int, validations: int):
        super().__init__(Command.WORK_COMPLETE)
        self.id = id
        self.sudoku = sudoku
        self.job = job
        self.validations = validations


class SudokuSolved(Message):
    """
    A Sudoku is solved.
    This message may be sent to all nodes.

    :param id: Sudoku UUID.
    :type id: str
    :param sudoku: Sudoku object.
    :type sudoku: Sudoku
    :param address: Address of the node that got the HTTP request.
    :type address: Address
    """

    def __init__(
        self,
        id: str,
        sudoku: Sudoku,
        address: Address,
    ):
        super().__init__(Command.SUDOKU_SOLVED)
        self.id = id
        self.sudoku = sudoku
        self.address = address


class P2PProtocol:
    @classmethod
    def send_msg(
        cls,
        connection: socket,
        message: Message,
    ) -> None:
        """Sends a message to the broker based on the command type."""
        try:
            msg = pickle.dumps(message)
            header = len(msg).to_bytes(2, byteorder="big")
            connection.send(header + msg)
        except Exception as e:
            raise P2PProtocolBadFormat(f"Error sending message: {e}")

    @classmethod
    def recv_msg(cls, connection: socket) -> Optional[Message]:
        """Receives through a connection a Message object."""
        try:
            h = int.from_bytes(connection.recv(2), "big")

            if h == 0:
                return None

            binary = connection.recv(h)
            return pickle.loads(binary)
        except Exception as e:
            raise P2PProtocolBadFormat(f"Error receiving message: {e}")


class P2PProtocolBadFormat(Exception):
    """Exception when the source message is not CDProto."""

    def __init__(self, original_msg: str = None):
        """Store the original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve the original message as a string."""
        return self._original
