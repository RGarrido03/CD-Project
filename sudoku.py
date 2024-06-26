import logging
import random
import time
from collections import deque

from custom_types import sudoku_type, row_type


class Sudoku:
    def __init__(self, sudoku: sudoku_type, base_delay=0.01, interval=10, threshold=5):
        self.grid = sudoku
        self.recent_requests = deque()
        self.base_delay = base_delay
        self.interval = interval
        self.threshold = threshold

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        """Limit the number of requests made to the Sudoku object."""
        if base_delay is None:
            base_delay = self.base_delay
        if interval is None:
            interval = self.interval
        if threshold is None:
            threshold = self.threshold

        current_time = time.time()
        self.recent_requests.append(current_time)
        num_requests = len(
            [t for t in self.recent_requests if current_time - t < interval]
        )

        if num_requests > threshold:
            delay = base_delay * (num_requests - threshold + 1)
            time.sleep(delay)

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += (
                    str(self.grid[i][j])
                    if self.grid[i][j] != 0
                    else f"\033[93m{self.grid[i][j]}\033[0m"
                )
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def update_row(self, row: int, values: row_type):
        """Update the values of the given row."""
        self.grid[row] = values

    def update_column(self, col: int, values: list[int]):
        """Update the values of the given column."""
        for row in range(9):
            self.grid[row][col] = values[row]

    def check_is_valid(
        self, row, col, num, base_delay=None, interval=None, threshold=None
    ):
        """Check if 'num' is not in the current row, column and 3x3 sub-box."""
        self._limit_calls(base_delay, interval, threshold)

        # Check if the number is in the given row or column
        for i in range(9):
            if self.grid[row][i] == num or self.grid[i][col] == num:
                return False

        # Check if the number is in the 3x3 sub-box
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if self.grid[start_row + i][start_col + j] == num:
                    return False

        return True

    def check_row(self, row, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False

        return True

    def check_column(self, col, base_delay=None, interval=None, threshold=None):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check col
        if (
            sum([self.grid[row][col] for row in range(9)]) != 45
            or len(set([self.grid[row][col] for row in range(9)])) != 9
        ):
            return False

        return True

    def check_square(self, row, col, base_delay=None, interval=None, threshold=None):
        """Check if the given 3x3 square is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check square
        if (
            sum([self.grid[row + i][col + j] for i in range(3) for j in range(3)]) != 45
            or len(
                set([self.grid[row + i][col + j] for i in range(3) for j in range(3)])
            )
            != 9
        ):
            return False

        return True

    def check(self, base_delay=None, interval=None, threshold=None):
        """Check if the given Sudoku solution is correct.

        You MUST incorporate this method without modifications into your final solution.
        """

        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i * 3, j * 3, base_delay, interval, threshold):
                    return False

        return True

    @classmethod
    def return_square(cls, square: int, grid: sudoku_type) -> list[list[int]]:
        start_row, start_col = (square // 3) * 3, (square % 3) * 3
        extracted_square = [
            [grid[i + start_row][j + start_col] for j in range(3)] for i in range(3)
        ]
        return extracted_square

    @classmethod
    def get_number_of_zeros_in_square(cls, square: int, grid: sudoku_type) -> int:
        start_row, start_col = (square // 3) * 3, (square % 3) * 3
        return sum(
            [
                1
                for i in range(3)
                for j in range(3)
                if grid[i + start_row][j + start_col] == 0
            ]
        )

    @classmethod
    def replace_square(cls, square: int, values: list[list[int]], grid: sudoku_type):
        start_row, start_col = (square // 3) * 3, (square % 3) * 3
        for i in range(3):
            for j in range(3):
                grid[i + start_row][j + start_col] = values[i][j]

    @classmethod
    def update_square(cls, square: int, grid: sudoku_type) -> tuple[sudoku_type, bool]:
        rows_idx = [i + ((square // 3) * 3) for i in range(3)]
        cols_idx = [i + ((square % 3) * 3) for i in range(3)]

        zeros_number = cls.get_number_of_zeros_in_square(square, grid)

        if zeros_number == 0:
            return grid, True

        logging.info(f"Updating square {square} with {zeros_number} zeros")

        for i in rows_idx:
            row = grid[i]
            for j in cols_idx:
                col = [grid[k][j] for k in range(9)]
                if grid[i][j] == 0:
                    while True:
                        new_value = random.randint(1, 9)
                        if (
                            new_value not in row
                            and new_value not in col
                            and new_value
                            not in [
                                num
                                for lst in cls.return_square(square, grid)
                                for num in lst
                            ]
                        ):
                            grid[i][j] = new_value
                            logging.info(f"Updated ({i}, {j}) with {new_value}")
                            return grid, zeros_number == 1


if __name__ == "__main__":
    sudoku = Sudoku(
        [
            [8, 9, 7, 1, 2, 4, 6, 3, 5],
            [5, 3, 1, 6, 7, 9, 2, 8, 4],
            [6, 4, 2, 3, 8, 5, 1, 7, 9],
            [1, 5, 4, 2, 9, 3, 8, 6, 7],
            [2, 8, 9, 7, 1, 6, 4, 5, 3],
            [3, 7, 6, 4, 5, 8, 9, 1, 2],
            [9, 2, 3, 8, 6, 7, 5, 4, 1],
            [7, 6, 5, 9, 4, 1, 3, 2, 8],
            [4, 1, 8, 5, 3, 2, 7, 9, 6],
        ]
    )

    print(sudoku)

    if sudoku.check():
        print("Sudoku is correct!")
    else:
        print("Sudoku is incorrect! Please check your solution.")
