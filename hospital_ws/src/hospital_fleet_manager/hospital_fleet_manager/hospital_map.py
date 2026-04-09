import networkx as nx


def build_hospital_map():
    """Build a simple hospital topology map."""
    G = nx.Graph()

    # Rooms and nodes
    rooms = [
        'Lobby', 'NurseStation', 'ER', 'WardA', 'WardB', 'WardC',
        'Pharmacy', 'Lab', 'Cafeteria', 'Radiology', 'ICU', 'Supply', 'MRI'
    ]
    G.add_nodes_from(rooms)

    # Bidirectional corridors
    edges = [
        ('Lobby', 'NurseStation'),
        ('NurseStation', 'ER'),
        ('NurseStation', 'WardA'),
        ('NurseStation', 'WardB'),
        ('NurseStation', 'Cafeteria'),
        ('ER', 'ICU'),
        ('WardA', 'WardC'),
        ('WardB', 'Supply'),
        ('WardC', 'Radiology'),
        ('Supply', 'Pharmacy'),
        ('Lab', 'Radiology'),
        ('Radiology', 'MRI'),
        ('MRI', 'ICU'),
        ('Pharmacy', 'Cafeteria'),
        ('Cafeteria', 'Lobby'),
        ('Lab', 'MRI'),
    ]
    G.add_edges_from(edges, weight=1.0)

    return G


def shortest_path_length(G, source, destination):
    """Return shortest distance between two points on the map."""
    if source not in G or destination not in G:
        raise ValueError(f"Node {source} or {destination} not in hospital map")

    return nx.shortest_path_length(G, source=source, target=destination, weight='weight')


def shortest_path(G, source, destination):
    """Return path sequence from source to destination."""
    if source not in G or destination not in G:
        raise ValueError(f"Node {source} or {destination} not in hospital map")

    return nx.shortest_path(G, source=source, target=destination, weight='weight')
