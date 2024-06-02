from enum import IntEnum


class Command(IntEnum):
    JOIN_PARENT = 1  # When node is created
    JOIN_PARENT_RESPONSE = 2  # List all nodes in network
    JOIN_OTHER = 3  # Join each node in the list above
    JOIN_OTHER_RESPONSE = 4  # Response from node, with current stats
    KEEP_ALIVE = 5  # Hey, you there, right?
    WORK_REQUEST = 10  # Give work to a node
    WORK_ACK = 11  # Ok, I'll do that
    WORK_COMPLETE = 12  # When a node finishes its job
    WORK_CANCEL = 13  # Cancel a job that other node already finished
    WORK_CANCEL_ACK = 14  # Acknowledge cancel


class Role(IntEnum):
    LINES = 1
    COLUMNS = 2
    SQUARES = 3
