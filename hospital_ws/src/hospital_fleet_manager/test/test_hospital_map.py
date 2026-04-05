import pytest

from hospital_fleet_manager.hospital_map import build_hospital_map, shortest_path_length


def test_build_hospital_map():
    g = build_hospital_map()
    assert len(g.nodes) == 10
    assert len(g.edges) == 10  # undirected graph has unique edges


def test_shortest_path_length():
    g = build_hospital_map()
    assert shortest_path_length(g, 'Lobby', 'NurseStation') == 1
    assert shortest_path_length(g, 'Lobby', 'ER') == 2


def test_invalid_node():
    g = build_hospital_map()
    with pytest.raises(ValueError):
        shortest_path_length(g, 'Invalid', 'Lobby')
