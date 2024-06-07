from enum import IntEnum


class Command(IntEnum):
    JOIN_PARENT = 1  # When node is created
    JOIN_PARENT_RESPONSE = 2  # List all nodes in network
    JOIN_OTHER = 3  # Join each node in the list above
    JOIN_OTHER_RESPONSE = 4  # Response from node, with current stats
    KEEP_ALIVE = 5  # Hey, you there, right?
    STORE_SUDOKU = 6
    WORK_REQUEST = 7  # Give work to a node
    WORK_ACK = 8  # Ok, I'll do that
    WORK_COMPLETE = 9  # When a node finishes its job
    SUDOKU_SOLVED = 10  # When a node solves a sudoku


class JobStatus(IntEnum):
    PENDING = 1
    IN_PROGRESS = 2
    COMPLETED = 3
