import pickle
from enum import Enum
from socket import socket
from typing import Optional

from consts import Command, Role
from custom_types import sudoku_type


# TODO: Join, work req, work rep, cancel work, keep alive ?


class Message:
    """Message Type."""

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


class StatsRequest(Message):
    def __init__(self):
        super().__init__(Command.STATS_REQUEST)


class StatsResponse(Message):
    def __init__(self, data: dict[str, tuple[int, int]]):
        super().__init__(Command.STATS_RESPONSE)
        self.data = data


class NetworkRequest(Message):
    def __init__(self):
        super().__init__(Command.NETWORK_REQUEST)


class NetworkResponse(Message):
    def __init__(self, data: dict[str, list[str]]):
        super().__init__(Command.NETWORK_RESPONSE)
        self.data = data


class SolveRequest(Message):
    def __init__(self, sudoku: sudoku_type, role: Role):
        super().__init__(Command.SOLVE_REQUEST)
        self.sudoku = sudoku
        self.role = role


class SolveResponse(Message):
    def __init__(self, sudoku: sudoku_type):
        super().__init__(Command.SOLVE_RESPONSE)
        self.sudoku = sudoku


class NewRole(Message):
    def __init__(self, role: Role):
        super().__init__(Command.NEW_ROLE)
        self.role = role


class P2PProtocol:
    @classmethod
    def stats_request(cls) -> StatsRequest:
        return StatsRequest()

    @classmethod
    def stats_response(cls, data: dict[str, tuple[int, int]] = None) -> StatsResponse:
        if data is None:
            data = {}
        return StatsResponse(data)

    @classmethod
    def network_request(cls) -> NetworkRequest:
        return NetworkRequest()

    @classmethod
    def network_response(
        cls, data: dict[str, tuple[int, int]] = None
    ) -> NetworkResponse:
        if data is None:
            data = {}
        return NetworkResponse(data)

    @classmethod
    def solve_request(cls, sudoku: sudoku_type, role: Role) -> SolveRequest:
        return SolveRequest(sudoku, role)

    @classmethod
    def solve_response(cls, sudoku: sudoku_type) -> SolveResponse:
        return SolveResponse(sudoku)

    @classmethod
    def new_role(cls, role: Role) -> NewRole:
        return NewRole(role)

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
