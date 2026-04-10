import networkx as nx


def build_hospital_map():
    """Build an extensive hospital topology map with multiple wings and departments."""
    G = nx.Graph()

    # Rooms and nodes - 25+ locations across hospital
    rooms = [
        # Main Lobby & Access
        'MainLobby', 'NorthEntrance', 'SouthEntrance', 'EmergencyEntry',
        # Emergency & Critical Care
        'ER', 'Trauma', 'ICU', 'PICU', 'NICU', 'CCU',
        # Medical Wards
        'WardA', 'WardB', 'WardC', 'WardD', 'WardE',
        # Surgery & Procedure Rooms
        'OperatingRoom1', 'OperatingRoom2', 'OperatingRoom3', 'Recovery',
        # Diagnostics & Imaging
        'Lab', 'Radiology', 'MRI', 'Ultrasound', 'CT',
        # Support Services
        'Pharmacy', 'Cafeteria', 'Supply', 'Sterilization',
        # Administration & Specialized
        'Administration', 'Morgue', 'Physical Therapy',
        # Nursing Stations
        'NursingStationN', 'NursingStationS', 'NursingStationE',
    ]
    G.add_nodes_from(rooms)

    # Bidirectional corridors - extensive network
    edges = [
        # Access points
        ('MainLobby', 'NorthEntrance'),
        ('MainLobby', 'SouthEntrance'),
        ('MainLobby', 'EmergencyEntry'),
        # Emergency cluster
        ('EmergencyEntry', 'ER'),
        ('ER', 'Trauma'),
        ('Trauma', 'ICU'),
        ('ER', 'NursingStationN'),
        # Critical care
        ('ICU', 'PICU'),
        ('PICU', 'NICU'),
        ('ICU', 'CCU'),
        ('CCU', 'Recovery'),
        # Ward distribution
        ('NursingStationN', 'WardA'),
        ('NursingStationN', 'WardB'),
        ('WardA', 'WardC'),
        ('WardB', 'WardD'),
        ('WardC', 'WardE'),
        ('NursingStationS', 'WardD'),
        ('NursingStationS', 'WardE'),
        # Surgery wing
        ('NursingStationN', 'OperatingRoom1'),
        ('OperatingRoom1', 'OperatingRoom2'),
        ('OperatingRoom2', 'OperatingRoom3'),
        ('OperatingRoom3', 'Recovery'),
        # Diagnostics hub
        ('NursingStationE', 'Lab'),
        ('Lab', 'Radiology'),
        ('Radiology', 'MRI'),
        ('Radiology', 'Ultrasound'),
        ('Radiology', 'CT'),
        ('MRI', 'CT'),
        # Support services
        ('MainLobby', 'Pharmacy'),
        ('MainLobby', 'Cafeteria'),
        ('Pharmacy', 'Supply'),
        ('Supply', 'Sterilization'),
        # Administration
        ('MainLobby', 'Administration'),
        ('Administration', 'Morgue'),
        # Physical therapy
        ('WardE', 'Physical Therapy'),
        ('Recovery', 'Physical Therapy'),
        # Additional connections
        ('Cafeteria', 'Supply'),
        ('Sterilization', 'OperatingRoom1'),
        ('Lab', 'ICU'),
        ('Pharmacy', 'ER'),
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
