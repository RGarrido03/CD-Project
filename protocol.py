import pickle
from enum import Enum
from socket import socket
from typing import Optional

from consts import Command, Role
from custom_types import Address


class Message:
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


class JoinParent(Message):
    """
    When the node is created and a parent is specified,
    send a request to that parent, to get the list of all nodes in the network.
    """

    def __init__(self):
        super().__init__(Command.JOIN_PARENT)


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

    def __init__(self):
        super().__init__(Command.JOIN_OTHER)


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
    :param sudoku: Sudoku grid.
    :type sudoku: list[list[int]]
    :param role: Role.
    :type role: Role
    """

    def __init__(self, id: str, sudoku: list[list[int]], role: Role):
        super().__init__(Command.WORK_REQUEST)
        self.id = id
        self.sudoku = sudoku
        self.role = role


class WorkAck(Message):
    """
    Acknowledge WorkRequest message.

    :param id: Job UUID.
    :type id: str
    """

    def __init__(self, id: str):
        super().__init__(Command.WORK_ACK)
        self.id = id


class WorkComplete(Message):
    """
    The job is complete.
    This message may be sent to all nodes (or just the one who requested? Let's see)

    It includes the number of validations, for updating the stats.
    Only validations are needed, the solved number is implicitly +1.

    :param id: Job UUID.
    :type id: str
    :param grid: Solved grid
    :type grid: list[list[int]]
    :param validations: Number of validations.
    :type validations: int
    """

    def __init__(self, id: str, grid: list[list[int]], validations: int):
        super().__init__(Command.WORK_COMPLETE)
        self.id = id
        self.grid = grid
        self.validations = validations


class WorkCancel(Message):
    """
    When a sudoku is completed on a node, the other ones don't need to find the solution anymore.
    This message cancels a job.

    :param id: Job UUID.
    :type id: str
    """

    def __init__(self, id: str):
        super().__init__(Command.WORK_CANCEL)
        self.id = id


class WorkCancelAck(Message):
    """
    Acknowledge WorkCancel message.
    It includes the number of validations, for updating the stats.
    In this case, the solved number is unchanged, since no solution was found in the node until then.

    :param id: Job UUID.
    :type id: str
    :param validations: Number of validations.
    :type validations: int
    """

    def __init__(self, id: str, validations: int):
        super().__init__(Command.WORK_CANCEL_ACK)
        self.id = id
        self.validations = validations


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
