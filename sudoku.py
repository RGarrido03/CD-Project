import time
from collections import deque


class Sudoku:
    def __init__(self, sudoku):
        self.grid = sudoku
        self.recent_requests = deque()

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        current_time = time.time()
        self.recent_requests.append(current_time)
        num_requests = len([t for t in self.recent_requests if current_time - t < 10])

        if num_requests > 5:
            delay = 0.01 * (num_requests - 5 + 1)
            time.sleep(delay)

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += str(self.grid[i][j])
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation


    def check_row(self, row, base_delay=0.01, interval=10, threshold=5):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.grid[row]) != 45:
            return False

        return True

    def check(self, base_delay=0.01, interval=10, threshold=5):
        """Check if the given Sudoku solution is correct.
        
        You MUST incorporate this method without modifications into your final solution.
        """
        for row in range(9):
            self.check_row(row, base_delay, interval, threshold)

        # Check columns
        for col in range(9):
            if sum([self.grid[row][col] for row in range(9)]) != 45:
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if sum([self.grid[i*3+k][j*3+l] for k in range(3) for l in range(3)]) != 45:
                    return False

        return True


if __name__ == "__main__":

    sudoku = Sudoku([
        [0,0,0,1,0,0,0,0,0],
        [0,0,0,3,2,0,0,0,0],
        [0,0,0,0,0,9,0,0,0],
        [0,0,0,0,0,0,0,7,0],
        [0,0,0,0,0,0,0,0,0],
        [0,0,0,9,0,0,0,0,0],
        [0,0,0,0,0,0,9,0,0],
        [0,0,0,0,0,0,0,0,3],
        [0,0,0,0,0,0,0,0,0]
    ])

    print(sudoku)

    if sudoku.check():
        print("Sudoku is correct!")
    else:
        print("Sudoku is incorrect! Please check your solution.")
