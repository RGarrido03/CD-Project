import threading
import time

import pytest
import requests

from gen import generate_sudoku, solve_sudoku
from node import Node


@pytest.fixture
def node_0():
    node = Node(8000, 6000, None, 0)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_1():
    node = Node(8001, 7001, "127.0.0.1:6000", 0)
    time.sleep(0.2)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_2():
    node = Node(8002, 7002, "127.0.0.1:6000", 0)
    time.sleep(0.2)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_3():
    node = Node(8003, 7003, "127.0.0.1:7002", 0)
    time.sleep(0.2)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


def test(node_0, node_1, node_2, node_3):
    gen_sudoku = generate_sudoku(3)

    response = requests.post(
        "http://localhost:8000/solve",
        json={"sudoku": gen_sudoku.grid},
    )

    solve_sudoku(gen_sudoku.grid)

    assert response.status_code == 200
    assert response.json()["sudoku"] == gen_sudoku.grid
