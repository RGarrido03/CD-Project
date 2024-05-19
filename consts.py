from enum import IntEnum


class Command(IntEnum):
    STATS_REQUEST = 1
    STATS_RESPONSE = 2
    NETWORK_REQUEST = 3
    NETWORK_RESPONSE = 4
    SOLVE_REQUEST = 5
    SOLVE_RESPONSE = 6
    NEW_ROLE = 7  # To be confirmed


class Role(IntEnum):
    LINES = 1
    COLUMNS = 2
    SQUARES = 3
