def subdivide_board(board):
    """Divide the board into 3x3 squares."""
    squares = []
    for i in range(0, 9, 3):
        for j in range(0, 9, 3):
            square = [row[j:j + 3] for row in board[i:i + 3]]
            squares.append(square)
    return squares
