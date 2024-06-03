from typing import Optional

from consts import JobStatus

Address = tuple[str, int]

row_type = list[int]
sudoku_type = list[row_type]

jobs_structure = list[tuple[JobStatus, Optional[Address]]]
