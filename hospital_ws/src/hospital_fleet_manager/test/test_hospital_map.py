import pytest

from hospital_fleet_manager.hospital_map import build_hospital_map, shortest_path, shortest_path_length


def test_build_hospital_map():
    g = build_hospital_map()
    assert len(g.nodes) == 34
    assert len(g.edges) >= 40
    assert "MainLobby" in g.nodes
    assert "ER" in g.nodes
    assert "NursingStationN" in g.nodes


def test_shortest_path_length():
    g = build_hospital_map()
    assert shortest_path_length(g, "MainLobby", "ER") == 2
    assert shortest_path_length(g, "ER", "ICU") == 2


def test_shortest_path_returns_valid_route():
    g = build_hospital_map()
    route = shortest_path(g, "MainLobby", "ICU")
    assert route[0] == "MainLobby"
    assert route[-1] == "ICU"
    assert len(route) >= 2


def test_invalid_node():
    g = build_hospital_map()
    with pytest.raises(ValueError):
        shortest_path_length(g, "Invalid", "MainLobby")
