import threading

import pytest
import requests

from gen import generate_sudoku, solve_sudoku
from node import Node


@pytest.fixture
def node_0():
    return Node(8000, 6000, None, 0)


@pytest.fixture
def node_1():
    return Node(8001, 6001, "127.0.0.1:6000", 0)


@pytest.fixture
def node_2():
    return Node(8002, 6002, "127.0.0.1:6000", 0)


@pytest.fixture
def node_3():
    return Node(8003, 6003, "127.0.0.1:6002", 0)


def test(node_0, node_1, node_2, node_3):
    gen_sudoku = generate_sudoku(3)

    response = requests.post(
        "http://localhost:8000/solve",
        json={"sudoku": gen_sudoku.grid},
    )

    solve_sudoku(gen_sudoku.grid)

    assert response.status_code == 200
    assert response.json() == gen_sudoku.grid

    assert node_0.p2p.validations > 0
    assert node_1.p2p.validations > 0
    assert node_2.p2p.validations > 0
    assert node_3.p2p.validations > 0
