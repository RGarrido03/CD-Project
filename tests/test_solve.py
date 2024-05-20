import threading

import pytest
import requests

from node import Node


@pytest.fixture
def node_0():
    node = Node(8000, 7000, None, 0)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_1():
    node = Node(8001, 7001, "127.0.0.1:7000", 0)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_2():
    node = Node(8002, 7002, "127.0.0.1:7000", 0)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


@pytest.fixture
def node_3():
    node = Node(8003, 7003, "127.0.0.1:7002", 0)

    thread = threading.Thread(target=node.run, daemon=True)
    thread.start()
    return node


def test(node_0, node_1, node_2, node_3):
    response = requests.post(
        "http://localhost:8000/solve",
        json={
            "sudoku": [
                [0, 0, 0, 1, 0, 0, 0, 0, 0],
                [0, 0, 0, 3, 2, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 9, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 7, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 9, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 9, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 3],
                [0, 0, 0, 0, 0, 0, 0, 0, 0],
            ]
        },
    )

    assert response.status_code == 200
    print(requests.get("http://localhost:8000/network").json())
    assert response.json() == [
        [8, 2, 7, 1, 5, 4, 3, 9, 6],
        [9, 6, 5, 3, 2, 7, 1, 4, 8],
        [3, 4, 1, 6, 8, 9, 7, 5, 2],
        [5, 9, 3, 4, 6, 8, 2, 7, 1],
        [4, 7, 2, 5, 1, 3, 6, 8, 9],
        [6, 1, 8, 9, 7, 2, 4, 3, 5],
        [7, 8, 6, 2, 3, 5, 9, 1, 4],
        [1, 5, 4, 7, 9, 6, 8, 2, 3],
        [2, 3, 9, 8, 4, 1, 5, 6, 7],
    ]

    assert node_0.validations > 0
    assert node_1.validations > 0
    assert node_2.validations > 0
    assert node_3.validations > 0
