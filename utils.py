from custom_types import Address


def subdivide_board(board):
    """Divide the board into 3x3 squares."""
    squares = []
    for i in range(0, 9, 3):
        for j in range(0, 9, 3):
            square = [row[j : j + 3] for row in board[i : i + 3]]
            squares.append(square)
    return squares


class AddressUtils:
    @classmethod
    def address_to_str(cls, address: Address) -> str:
        return ":".join(str(prop) for prop in address)

    @classmethod
    def str_to_address(cls, address: str) -> Address:
        (addr, port) = address.split(":")
        return addr, int(port)
